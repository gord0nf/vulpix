import queue
import threading
from typing import Callable, Protocol

from vulpix import VulpixError, utils
from vulpix.logging import (
    Logger, LoggerAdapter, get_logger, logger_is_verbose, set_console_log_fmt
)

type Task = tuple[str, Callable, tuple, dict] # like task_name, func, args, kwargs

class ThreadedTaskQueue(queue.Queue[Task]):
    """
    queue that spawns a bunch of worker threads equal to the max queue length. this way, when a task
    is requested to run, it holds the running code until it actually is put into the queue and has a
    worker running it.
    """

    # params like args, kwargs, task_name, task_queue
    type TaskFunction = Callable[[tuple, dict, str, ThreadedTaskQueue], BaseException | None]

    logger: Logger
    threads: list[WorkerThread]
    exit_event: threading.Event
    done_broadcast: utils.Broadcast
    completed_tasks: dict[str, bool]  # task_name: was_successful
    completed_tasks_lock: threading.Lock

    def run_task(self, name: str, f: TaskFunction, *args, **kwargs):
        self.logger.debug(f"adding task '{name}', {f.__name__}")
        self.put((name, f, args, kwargs), block=True)

    def _thread_should_die(self):
        return self.exit_event.is_set() and self.empty() and self.unfinished_tasks == 0

    def _get_task_logger(self, task_name: str) -> Logger:
        logger = get_logger(f"tasks/{task_name}", verbose=logger_is_verbose(self.logger))
        name = utils.Colors.CYAN + task_name + utils.Colors.RESET
        set_console_log_fmt(logger, f"\t%(levelname)s> {name}> %(message)s")
        return logger

    class WorkerThread(threading.Thread):
        q: ThreadedTaskQueue
        current_task: str | None


        DONE = utils.Colors.GREEN + "done" + utils.Colors.RESET
        FAIL = utils.Colors.RED + "failed" + utils.Colors.RESET

        def __init__(self, q: ThreadedTaskQueue):
            super().__init__()
            self.q = q
            self.current_task = None

        def run(self):
            while True:
                try:
                    self.current_task, f, args, kwargs = self.q.get(timeout=0.2)
                except queue.Empty:
                    if self.q._thread_should_die():
                        break
                    continue

                self.q.logger.debug(f"task starting: {self.current_task}")

                error = f(args, kwargs, task_name=self.current_task, task_queue=self.q)
                success = error is None

                self.q.task_done()
                self.q.logger.info(f"{self.current_task} ({self.DONE if success else self.FAIL})")
                with self.q.completed_tasks_lock:
                    self.q.completed_tasks[self.current_task] = success
                self.current_task = None
                self.q.done_broadcast.broadcast()

    def __init__(self, n_threads: int, logger: Logger) -> None:
        super().__init__(n_threads)
        self.logger = logger
        self.threads = []
        self.exit_event = threading.Event()
        self.done_broadcast = utils.Broadcast()
        self.completed_tasks = {}
        self.completed_tasks_lock = threading.Lock()

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

    def wait_for_tasks(self, tasks: list[str]):
        """holds until the target tasks all exist in self.completed_tasks"""
        satisfied = False
        while not satisfied:
            self.done_broadcast.wait()
            with self.completed_tasks_lock: # immediately get lock
                satisfied = all(t in self.completed_tasks for t in tasks)

def task_function(f: Callable) -> ThreadedTaskQueue.TaskFunction:
    """decorator to mark a function as a task compatible with ThreadedTaskQueue usage"""

    def wrapped_function(args: tuple, kwargs: dict, task_name: str, task_queue: ThreadedTaskQueue):
        kwargs["name"] = task_name
        kwargs["queue"] = task_queue
        kwargs["logger"] = task_queue._get_task_logger(task_name)

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
