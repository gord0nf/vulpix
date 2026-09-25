import sys
import re
import random
import threading
from contextlib import AbstractContextManager

from vulpix.core import VulpixError
from vulpix.cli import logging
from vulpix.cli.logging import term, term_lock
from vulpix.core.blueprint import Blueprint
from vulpix.core.tasks import ThreadedTaskQueue

def sugary(title: str, color1: function, color2: function, color3: function) -> str:
    title = color1(" ~(￣▽￣)~* ") + color2("   " + title.upper() + "   ")
    remainder = color3(" " * (term.width - term.length(title)))
    return term.black(title + remainder)

def task_summary(completed_tasks: dict[str, bool]) -> str:
    fmark, smark = term.red("failure"), term.green("success")
    failed = [f"  - {task} ({fmark})" for task, success in completed_tasks.items() if not success]
    succeeded = [f"  - {task} ({smark})" for task, success in completed_tasks.items() if success]
    lines = [*failed, *succeeded]
    lines.sort()
    return "\n".join(lines) + "\n"

class TaskSection(ThreadedTaskQueue):
    verbose: bool = False

    name: str
    alt_screen: bool = True
    show_tasks: re.Pattern = re.compile(".*")
    tasks_failed: bool

    header_title: str
    footer_title: str
    footer_height: int

    _fullscreen: AbstractContextManager
    _scroll_region: AbstractContextManager

    def __init__(self, name: str, blueprint: Blueprint, logger: logging.Logger):
        super().__init__(blueprint.settings.threads, logger)
        self.name = name
        self.alt_screen = blueprint.settings.alt_screen

        self.header_title = sugary(name, term.on_turquoise, term.on_aquamarine3, term.on_teal)
        self.footer_title = sugary("tasks", term.on_fuchsia, term.on_maroon1, term.on_mediumorchid4)
        self.footer_height = min(blueprint.settings.threads + 1, term.height // 2) # +1 for title

        self.logger.debug(f"task_section footer height: {self.footer_height}")
        if self.footer_height <= 0:
            raise VulipxError("not enough height for task section footer")

    def _get_task_logger(self, task_name: str) -> logging.Logger:
        logger = super()._get_task_logger(task_name)
        task_name = term.cyan(task_name)
        logging.attach_console_logging(logger, self.verbose, prefix=("\t", f" {task_name}>"))
        return logger

    def _update_footer(self):
        with self.mutex:
            running_tasks = [t.current_task for t in self.threads if t.current_task]
        n_running_tasks = len(running_tasks)

        with term_lock, term.location(0, term.height - self.footer_height):
            label = term.yellow("running")
            for i in range(self.footer_height):
                if n_running_tasks > 0:
                    if i == 0:
                        sys.stdout.write(self.footer_title)
                        continue
                    task_i = i - 1

                    if i + 1 == self.footer_height and task_i + 1 < n_running_tasks:
                        sys.stdout.write(term.yellow("..."))
                    elif task_i < n_running_tasks:
                        sys.stdout.write(running_tasks[task_i] + f" ({label})")
                sys.stdout.write(term.clear_eol + "\n\r")
            sys.stdout.flush()

    def _post_task_callback(self, task_name: str, exc: Exception | None):
        super()._post_task_callback(task_name, exc)
        label = term.red("failed") if exc else term.green("succeeded")
        self.logger.info(f"{task_name} ({label})")

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
        em = random.choice(["(┬┬﹏┬┬)", "(^人^)", "(￣︿￣)"])
        self.logger.info(term.orchid(em) + " " + term.maroon1(self.name.upper()))

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

        # summary
        self.tasks_failed = any(not status for status in self.completed_tasks.values())
        if len(self.completed_tasks) > 0:
            em = term.red("＞︿＜") if self.tasks_failed else term.green("(✿ ◠‿◠)")
            print(f"\n[{em}] summary:\n" + task_summary(self.completed_tasks))
        return return_value
