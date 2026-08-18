from logging import Logger
import threading
from queue import Queue
from typing import Callable

from cli import log

type TaskFunction = Callable[[Logger], None]
type Task = tuple[str, TaskFunction, tuple, dict]  # like name, func, *args, **kwargs


class TaskQueue(Queue[Task]):
    TIMEOUT = 30
    logger: Logger

    def __init__(self, maxsize: int, logger: Logger) -> None:
        super().__init__(maxsize)
        self.logger = logger

    def put_task(self, name: str, f: TaskFunction, *args, **kwargs):
        self.put((name, f, args, kwargs), block=True, timeout=self.TIMEOUT)

    def _task_start_callback(self, name: str) -> None:
        pass

    def _task_end_callback(self, name: str, exc: BaseException | None) -> None:
        pass


class ThreadedTaskQueue(TaskQueue):

    class WorkerThread(threading.Thread):
        def __init__(self, task_queue: TaskQueue):
            super().__init__()
            self.task_queue = task_queue

        def run(self):
            while True:
                task, f, args, kwargs = self.task_queue.get()
                self.task_queue._task_start_callback(task)

                error: BaseException | None = None
                task_logger = log.get_logger(f"tasks/{task}")
                task_logger.info("running new task")
                try:
                    f(task_logger, *args, **kwargs)
                except BaseException as e:
                    task_logger.critical("task failed")
                    error = e
                else:
                    task_logger.info("task succeeded")

                self.task_queue.task_done()
                self.task_queue._task_end_callback(task, error)

    threads: list[WorkerThread]
    completed_tasks: dict[str, bool]  # task_name: was_successful

    def _task_start_callback(self, name: str) -> None:
        self.logger.debug(f"task started: {name}")

    def _task_end_callback(self, name: str, exc: BaseException | None) -> None:
        self.logger.debug(f"task exited: {name} (exc: {exc})")
        self.completed_tasks[name] = exc is None

    def __init__(self, n_threads: int, logger: Logger) -> None:
        super().__init__(maxsize=n_threads, logger=logger)

    def __enter__(self):
        # start worker threads
        self.threads = []
        for _ in range(self.maxsize):
            thread = ThreadedTaskQueue.WorkerThread(self)
            self.threads.append(thread)
            thread.start()

    def __exit__(self):
        for thread in self.threads:
            thread.join()
        return False
