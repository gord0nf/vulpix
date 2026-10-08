"""utility functions to standardize manager task naming conventions, plus it's more readable"""

import re
from dataclasses import dataclass

from vulpix.core.tasks import ThreadedTaskQueue as Queue


@dataclass(frozen=True)
class ManagerTask:
    verb: str
    manager: str
    package: str = ""

    @property
    def name(self) -> str:
        return (
            f"{self.verb}[{self.package + '@' if self.package else ''}{self.manager}]"
        )

    @classmethod
    def install(cls, package: str, manager: str):
        return cls("install", manager, package)

    @classmethod
    def update(cls, package: str, manager: str):
        return cls("update", manager, package)

    @classmethod
    def reinstall(cls, package: str, manager: str):
        return cls("reinstall", manager, package)

    @classmethod
    def uninstall(cls, package: str, manager: str):
        return cls("uninstall", manager, package)

    @classmethod
    def config(cls, package: str, manager: str):
        return cls("config", manager, package)

    def run(
        self,
        queue: Queue,
        f: Queue.TaskFunction,
        args: tuple | None = None,
        kwargs: dict | None = None,
    ):
        queue.run_task(self.name, f, *(args or ()), **(kwargs or {}))


package_task_pattern = re.compile("^(.+)\\[(.+)@(.+)\\]$")


def completed_package_tasks(og: dict[str, bool]) -> dict[ManagerTask, bool]:
    """filters out manager package tasks and returns with dict keys as parsed ManagerTasks"""
    parsed: dict[ManagerTask, bool] = {}
    for task_name, status in og.items():
        match = package_task_pattern.match(task_name)
        if match:
            task = ManagerTask(match.group(1), match.group(3), match.group(2))
            parsed[task] = status

    return parsed
