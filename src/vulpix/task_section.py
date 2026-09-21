import sys
import re
import threading
from blessed import Terminal
from contextlib import AbstractContextManager

from vulpix import VulpixError, logging
from vulpix.core.blueprint import Blueprint
from vulpix.core.tasks import ThreadedTaskQueue

term = Terminal()

def sugary(title: str, color1: function, color2: function, color3: function) -> str:
    title = color1(" ~(￣▽￣)~* ") + color2("   " + title.upper() + "   ")
    remainder = color3(" " * (term.width - term.length(title)))
    return term.black(title + remainder)

class TaskSection(ThreadedTaskQueue):
    alt_screen: bool = True
    show_tasks: re.Pattern = re.compile(".*")

    header_title: str
    footer_title: str
    footer_height: int

    _fullscreen: AbstractContextManager
    _scroll_region: AbstractContextManager


    def __init__(self, name: str, blueprint: Blueprint, logger: logging.Logger):
        super().__init__(blueprint.settings.threads, logger)
        self.alt_screen = blueprint.settings.alt_screen
        self.header_title = sugary(name, term.on_turquoise, term.on_aquamarine3, term.on_teal)
        self.footer_title = sugary("tasks", term.on_fuchsia, term.on_maroon1, term.on_mediumorchid4)
        self.footer_height = min(blueprint.settings.threads + 1, term.height // 2) # +1 for title
        self.logger.debug(f"task_section footer height: {self.footer_height}")
        if self.footer_height <= 0:
            raise VulipxError("not enough height for task section footer")

    def _get_task_logger(self, task_name: str) -> logging.Logger:
        logger = super()._get_task_logger(task_name)
        if self.alt_screen and not self.show_tasks.match(task_name):
            logging.hide_logger(logger)
        return logger

    def _update_footer(self):
        with self.mutex:
            running_tasks = [t.current_task for t in self.threads if t.current_task]
        n_running_tasks = len(running_tasks)

        with logging.console_lock, term.location(0, term.height - self.footer_height):
            for i in range(self.footer_height):
                if n_running_tasks > 0:
                    if i == 0:
                        sys.stdout.write(self.footer_title)
                        continue
                    task_i = i - 1

                    if i + 1 == self.footer_height and task_i + 1 < n_running_tasks:
                        sys.stdout.write(term.yellow("..."))
                    elif task_i < n_running_tasks:
                        sys.stdout.write(term.yellow("running " + running_tasks[task_i]))
                sys.stdout.write(term.clear_eol + "\n\r")
            sys.stdout.flush()

    def run_task(self, name: str, f: TaskFunction, *args, **kwargs):
        """updates footer when task started"""
        super().run_task(name, f, *args, **kwargs)
        if self.alt_screen:
            self._update_footer()

    def _update_footer_thread(self):
        """updates footer when task finishes"""
        while not self._thread_should_die():
            self.done_broadcast.wait()
            self._update_footer()

    def __enter__(self):
        # init task section screen
        if self.alt_screen:
            self.logger.info('entering alt screen')
            self._fullscreen = term.fullscreen()
            self._fullscreen.__enter__()
            sys.stdout.write(term.clear) 
            self._scroll_region = term.scroll_region(top=1,
                height=term.height - self.footer_height - 1)
            self._scroll_region.__enter__()
            sys.stdout.write(term.home + self.header_title + "\n")

            # no need to save thread var for join, since it should self desctruct
            threading.Thread(target=self._update_footer_thread).start()

        return super().__enter__()

    def __exit__(self, *exc_args):
        return_value = super().__exit__(*exc_args)
        if self.alt_screen:
            self._scroll_region.__exit__(*exc_args)
            self._fullscreen.__exit__(*exc_args)
        return return_value
