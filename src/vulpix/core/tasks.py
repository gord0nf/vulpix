import queue
import threading
import logging
from typing import Callable, Protocol

from vulpix import VulpixError
from vulpix.logging import get_logger

type Task = tuple[str, Callable, tuple, dict] # like task_name, func, args, kwargs

class ThreadedTaskQueue(queue.Queue[Task]):
    """
    queue that spawns a bunch of worker threads equal to the max queue length. this way, when a task
    is requested to run, it holds the running code until it actually is put into the queue and has a
    worker running it.
    """

    # params like args, kwargs, task_name, task_queue
    type TaskFunction = Callable[[tuple, dict, str, ThreadedTaskQueue], BaseException | None]

    logger: logging.Logger
    threads: list[WorkerThread]
    exit_event: threading.Event
    completed_tasks: dict[str, bool]  # task_name: was_successful
    completed_tasks_lock: threading.Lock

    def run_task(self, name: str, f: TaskFunction, *args, **kwargs):
        self.logger.debug(f"adding task '{name}', {f.__name__}")
        self.put((name, f, args, kwargs), block=True)

    def run_foreground_task(self, name: str, f: TaskFunction, *args, **kwargs):
        if "_done_event" in kwargs:
            raise Exception("ThreadedTaskQueue requires ownership of _done_event kwarg")
        done_event = threading.Event()
        kwargs["_done_event"] = done_event
        self.run_task(name, f, args, kwargs)
        done_event.wait()

    class WorkerThread(threading.Thread):
        q: ThreadedTaskQueue

        def __init__(self, q: ThreadedTaskQueue):
            super().__init__()
            self.q = q

        def run(self):
            while True:
                try:
                    task_name, f, args, kwargs = self.q.get(timeout=0.2)
                except queue.Empty:
                    if self.q.exit_event.is_set() and self.q.empty() and self.q.unfinished_tasks == 0:
                        break
                    continue

                self.q.logger.debug(f"task starting: {task_name}")

                # check for the _done_event used by run_foreground_task()
                done_event: threading.Event | None = None
                if "_done_event" in kwargs and isinstance(kwargs["_done_event"], threading.Event):
                    done_event = kwargs.pop("_done_event")

                error = f(args, kwargs, task_name=task_name, task_queue=self.q)

                self.q.task_done()
                self.q.logger.debug(f"task exited: {task_name} (exc: {error})")
                with self.q.completed_tasks_lock:
                    self.q.completed_tasks[task_name] = error is None
                if done_event:
                    done_event.set()

    def __init__(self, n_threads: int, logger: logging.Logger) -> None:
        super().__init__(n_threads)
        self.logger = logger
        self.threads = []
        self.completed_tasks = {}
        self.completed_tasks_lock = threading.Lock()
        self.exit_event = threading.Event()

    def __enter__(self):
        # start worker threads
        self.logger.debug(f"spawning {self.maxsize} threads")
        for _ in range(self.maxsize):
            thread = ThreadedTaskQueue.WorkerThread(self)
            self.threads.append(thread)
            thread.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.debug(f"joining {len(self.threads)} threads")
        self.exit_event.set()
        for thread in self.threads:
            thread.join()
        return False


def task_function(f: Callable) -> ThreadedTaskQueue.TaskFunction:
    """decorator to mark a function as a task compatible with ThreadedTaskQueue usage"""

    def wrapped_function(args: tuple, kwargs: dict, task_name: str, task_queue: ThreadedTaskQueue):
        kwargs["name"] = task_name
        kwargs["queue"] = task_queue

        # logger with prefix
        class PrefixAdapter(logging.LoggerAdapter):
            def process(self, msg, kwargs):
                return f"[{task_name}] {msg}", kwargs
        logger = get_logger(f"tasks/{task_name}", verbose=task_queue.logger.verbose)
        kwargs["logger"] = PrefixAdapter(logger)

        error: BaseException | None = None
        try:
            kwargs["logger"].info("running new task")
            f(*args, **kwargs)
        except VulpixError as e:
            error = e
            kwargs["logger"].critical(e.message)
        except BaseException as e:
            error = e
            kwargs["logger"].debug("exception raised", exc_info=True)
            kwargs["logger"].critical("task failed")
        else:
            kwargs["logger"].info("task succeeded")

        return error
    
    wrapped_function.__name__ = f.__name__
    return wrapped_function
