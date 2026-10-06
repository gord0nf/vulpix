"""
a config manager that allows the user to create scripts for each package that get run by this
manager.

it places the burden of actual configuration on you (the user), cause you have to create the
scripts. the script dir should be formatted like:

```
$VULPIX_CONFIG/scripts/
├─ ...general root scripts that run on every config
├─ $PACKAGE.d/
│  └─ ...scripts that run on every config of this package
└─ ...other *.d dirs for package configs
```

for example:

```
$VULPIX_CONFIG/scripts/
├─ 00-some-system-script.py
├─ 10-windows-only-script.ps1
├─ 10-unix-only-script.sh
├─ 10-will-still-run-if-exec.exe
├─ 50-upstream-script.py
├─ python.d/
│  ├─ 10-generic-config.py
│  ├─ 20-setup-base-packages.py
│  ├─ 20-setup-base-packages.py
│  └─ ...more scripts
├─ ...other general scripts
└─ ...other *.d dirs for package configs
```

as the above example shows, this manager also supports numbered script names like
`00-do-something.py`, which enables asynchronous script execution. the assumption is that all
scripts at the same numbered level can be run in parallel.

all files in the root dir or a `*.d` dir that are executable or end with ".sh"/".ps1"/".py" will
attempt to be run, regardless of whether they have a level number. scripts in `{PACKAGE}.d` dir will
only run if the `{PACKAGE}` is passed to this manager.

TODO: interface for passing config?
"""

import importlib.util
import inspect
import itertools
import re
from collections.abc import Generator
from pathlib import Path
from typing import Any

from vulpix.config_managers import ConfigManager, ManagerTask
from vulpix.core import VulpixError, dirs, logging, system
from vulpix.core.tasks import ThreadedTaskQueue, task_function
from vulpix.utils import LoggedCommand, accepts_kwarg, is_executable, path_as_salt

SCRIPTS_DIR = dirs.VULPIX_CONFIG / "config"


class Script:
    path: Path
    target_level: int | None = None
    target_package: str | None = None
    target_os: system.Os | None = None

    _level_prefix_pattern = re.compile("^(\\d+).*")

    @staticmethod
    def is_script(path: Path) -> bool:
        return path.is_file() and (
            is_executable(path) or path.suffix in [".py", ".sh", ".ps1"]
        )

    def __init__(self, path: Path):
        self.path = path.resolve()

        # check level prefix
        if match := self._level_prefix_pattern.match(self.path.stem):
            self.target_level = int(match.group(1))

        # check if package script
        if self.path.parent.parent.samefile(SCRIPTS_DIR):
            package_dir = self.path.parent.name
            if package_dir.endswith(".d"):
                self.target_package = package_dir[:-2]

        # check if script targets os
        match self.path.suffix:
            case ".sh":
                self.target_os = "linux"
            case ".ps1":
                self.target_os = "windows"

    def _run_as_python_script(self, **kwargs):
        """
        a python script is run by importing it. optionally, it looks for a `main` method which can
        accept any of the kwargs passed to this function

        usually they are the following args:

        - config: Any
        - logger: logging.Logger
        - queue: ThreadedTaskQueue
        """
        logger = kwargs["logger"]
        module_name = f"config_{self.path.stem.split('.')[0]}"
        spec = importlib.util.spec_from_file_location(module_name, self.path)
        if spec is None or spec.loader is None:
            raise VulpixError(f"could not load spec for {self.path}")

        script_module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(script_module)
            if hasattr(script_module, "main"):
                main = script_module.main
                if callable(main):
                    sig = inspect.signature(main)
                    kwargs = {k: v for k, v in kwargs.items() if accepts_kwarg(sig, k)}
                    main(**kwargs)
        except Exception as e:  # noqa: BLE001
            logger.error(str(e))
            raise VulpixError("config script failed")

    @task_function
    def run(self, config: Any, logger: logging.Logger, queue: ThreadedTaskQueue, **_):
        # prefer python obviously
        if self.path.suffix == ".py":
            self._run_as_python_script(config=config, logger=logger, queue=queue)
            return

        # TODO: figure out how to pass config to non-python scripts

        # fall back to external script execution
        if is_executable(self.path):
            cmd = [str(self.path)]
        elif self.path.suffix == ".ps1":
            cmd = ["powershell", str(self.path)]
        elif self.path.suffix == ".sh":
            cmd = ["sh", str(self.path)]
        else:
            raise VulpixError(f"no way to execute script: {self.path}")

        LoggedCommand(*cmd, logger=logger).run()

    def as_task(self) -> ManagerTask:
        name = path_as_salt(self.path.relative_to(SCRIPTS_DIR))
        return ManagerTask.config(name, manager="scripts")


def find_scripts() -> list[Script]:
    paths = [
        p
        for p in itertools.chain.from_iterable(
            [SCRIPTS_DIR.glob("*"), SCRIPTS_DIR.glob("*.d/*")]
        )
        if Script.is_script(p)
    ]
    return [Script(p) for p in paths]


def script_rounds(scripts: list[Script]) -> Generator[list[Script]]:
    """
    scripts are grouped into rounds by the digit prefix (e.g. 00-script.py). the assumption is
    that all the scripts in a round can be run in parallel. level-less scripts are run in the final
    round.
    """
    levels = [s.target_level for s in scripts if s.target_level is not None]
    levels.sort()
    for level in levels:
        yield [s for s in scripts if s.target_level == level]

    remainder = [s for s in scripts if s.target_level is None]
    if len(remainder) > 0:
        yield remainder


class ScriptsManager(ConfigManager):
    def check_config(self, config: Any) -> None:
        """any config can be passed to user scripts."""
        # maybe TODO: allow user to define their own check_config script

    @task_function
    def apply_config(
        self,
        config: Any,
        packages: list[str],
        logger: logging.Logger,
        queue: ThreadedTaskQueue,
    ) -> None:
        scripts = [
            s
            for s in find_scripts()
            if (not s.target_os or s.target_os == system.OS)
            and (not s.target_package or s.target_package in packages)
        ]
        logger.debug(f"scripts: {scripts}")
        if len(scripts) == 0:
            logger.warning("no scripts to run")

        for round_scripts in script_rounds(scripts):
            logger.debug(f"round: {[s.path for s in round_scripts]}")
            round_tasks: list[str] = []
            for script in round_scripts:
                task = script.as_task()
                task.run(queue, script.run, args=(config,))
                round_tasks.append(task.name)
            queue.wait_for_tasks(round_tasks)


config_manager_class = ScriptsManager
