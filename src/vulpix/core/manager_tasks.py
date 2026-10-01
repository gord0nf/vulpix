"""utility functions to standardize manager task naming conventions, plus it's more readable"""

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
