from typing import Any

from vulpix.core import logging
from vulpix.core.tasks import task_function, ThreadedTaskQueue
from vulpix.config_managers import ConfigManager

class ScriptsManager(ConfigManager):
    def check_config(self, config: Any) -> None:
        pass

    @task_function
    def apply_config(
        self,
        config: Any,
        packages: list[str],
        logger: logging.Logger,
        queue: ThreadedTaskQueue
    ) -> None:
        logger.debug(f"config: {config}")
        logger.debug(f"packages: {packages}")
        logger.info("scripts config manager TODO")

config_manager_class = ScriptsManager
