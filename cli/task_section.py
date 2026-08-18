from logging import Logger

from cli import log, tasks


class TaskSection(tasks.ThreadedTaskQueue):
    section_name: str
    alt_screen: bool

    def __init__(
        self,
        section_name: str,
        n_threads: int,
        alt_screen: bool = False,
        logger: Logger = log.main,
    ) -> None:
        super().__init__(n_threads, logger)
        self.section_name = section_name
        self.alt_screen = alt_screen

    def __enter__(self):
        # fancy ncurses stuff
        return super().__enter__()

    def __exit__(self):
        super().__exit__()
        # fancy ncurses stuff
        return False
