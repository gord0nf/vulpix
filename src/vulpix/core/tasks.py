import queue
import threading
import inspect
from typing import Any
from collections.abc import Callable

from vulpix.utils import VulpixError, Broadcast, logging, accepts_kwarg

type Task = tuple[str, Callable, tuple, dict] # like task_name, func, args, kwargs

class ThreadedTaskQueue(queue.Queue[Task]):
    """
    queue that spawns a bunch of worker threads equal to the max queue length. this way, when a task
    is requested to run, it holds the running code until it actually is put into the queue and has a
    worker running it.
    """

    type TaskFunction = Callable[..., Exception | None]

    logger: logging.Logger
    threads: list[WorkerThread]
    exit_event: threading.Event
    done_broadcast: Broadcast
    completed_tasks: dict[str, bool]  # task_name: was_successful
    completed_tasks_lock: threading.Lock

    def run_task(self, name: str, f: TaskFunction, *args, **kwargs):
        self.logger.debug(f"adding task '{name}', {f.__name__}")
        self.put((name, f, args, kwargs), block=True)

    def _thread_should_die(self):
        return self.exit_event.is_set() and self.empty() and self.unfinished_tasks == 0

    def _get_task_logger(self, task_name: str) -> logging.Logger:
        logger = logging.getLogger(f"tasks/{task_name}")
        logging.attach_log_file(logger)
        return logger
    
    def _post_task_callback(self, task_name: str, exc: Exception | None):
        with self.completed_tasks_lock:
            self.completed_tasks[task_name] = exc is None

    class WorkerThread(threading.Thread):
        q: ThreadedTaskQueue
        current_task: str | None

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

                task_logger = self.q._get_task_logger(self.current_task)

                error: Exception | None = None
                try:
                    f(*args, **kwargs, name=self.current_task, queue=self.q, logger=task_logger)
                except VulpixError as e:
                    error = e
                    task_logger.critical(e.message)
                except Exception as e:
                    error = e
                    task_logger.debug("exception raised", exc_info=True)
                    task_logger.critical("failure")
                else:
                    task_logger.info("success")

                self.q.task_done()
                self.q._post_task_callback(self.current_task, error)
                self.current_task = None
                self.q.done_broadcast.broadcast()

    def __init__(self, n_threads: int, logger: logging.Logger) -> None:
        super().__init__(n_threads)
        self.logger = logger
        self.threads = []
        self.exit_event = threading.Event()
        self.done_broadcast = Broadcast()
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

    sig = inspect.signature(f)

    def wrapped(
        *args: Any,
        name: str,
        queue: ThreadedTaskQueue,
        logger: logging.Logger,
        **kwargs: Any
    ) -> Exception | None:
        if accepts_kwarg(sig, "name"):
            kwargs["name"] = name
        if accepts_kwarg(sig, "queue"):
            kwargs["queue"] = queue
        if accepts_kwarg(sig, "logger"):
            kwargs["logger"] = logger

        logger.debug(f"task: {name} (args={args}, kwargs={kwargs})")
        f(*args, **kwargs)
    
    wrapped.__name__ = f.__name__ # not necessary, just for debugging
    return wrapped
