import os
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Self, cast

import yaml
from dacite import DaciteError

from vulpix import config_managers, package_managers
from vulpix.utils import (
    DataclassFile,
    DataclassOps,
    VulpixError,
    logging,
    merge_dicts,
)

load_func = yaml.safe_load
dump_func = yaml.dump


@dataclass
class Settings:
    threads: int | None = None
    alt_screen: bool | None = None
    abort_uninstall_threshold: int | None = None
    apt_mode: Literal["safe", "strict"] | None = None

    def set_defaults(self):
        if self.threads is None:
            cpu_count = os.cpu_count()
            self.threads = cpu_count + 4 if cpu_count else 4
        if self.alt_screen is None:
            self.alt_screens = True
        if self.abort_uninstall_threshold is None:
            self.abort_uninstall_threshold = 10
        if self.apt_mode is None:
            self.apt_mode = "safe"


@dataclass
class Blueprint:
    # target packages for each package manager to align to (dict like {manager: package_list})
    packages: dict[str, list[str]]

    # target config for each config manager to "align to" (quotes because the manager can really do
    # whatever it wants) (dict like {manager: config_struct}; see individual config manager
    # documentation for specific config_struct shape)
    configs: dict[str, Any]

    # path to dotfiles repo directory (optional)
    dotfiles: str | None = None

    # vulpix settings (optional)
    settings: Settings | None = None

    # allows extending other blueprints (optional)
    extends: list[str] | None = None

    def __post_init__(self):
        # verify package managers and packages
        for manager_id, packages in self.packages.items():
            try:
                manager = package_managers.get_manager(manager_id)
                manager.check_packages(packages)
            except package_managers.ManagerUnsupported as e:
                raise ValueError(f"manager '{e.manager}' not supported: {e.message}")
            except package_managers.InvalidPackage as e:
                raise ValueError(str(e))

        # verify config managers and configs
        for manager_id, config in self.configs.items():
            try:
                manager = config_managers.get_manager(manager_id)
                manager.check_config(config)
            except config_managers.ManagerUnsupported as e:
                raise ValueError(f"manager '{e.manager}' not supported: {e.message}")
            except config_managers.InvalidBlueprintConfig as e:
                raise ValueError(str(e))

    def set_defaults(self):
        if self.dotfiles is None:
            self.dotfiles = ""
        if self.extends is None:
            self.extends = []
        if self.settings is None:
            self.settings = Settings()
        self.settings.set_defaults()

    def extended_paths(self, extending_bp_path: Path) -> list[Path]:
        paths: list[Path] = []
        if self.extends:
            for extended in self.extends:
                path = Path(extended).expanduser()
                if not path.is_absolute():
                    path = extending_bp_path.parent / path
                if not path.exists():
                    raise ValueError(f"extended path does not exist: {path}")
                paths.append(path)
        return paths


class ExpandedBlueprint(Blueprint):
    """
    represts expanded blueprint after 1) resolving and merging extended blueprints and 2) apply
    defaults for optional fields.
    """

    dotfiles: str  # pyright: ignore [reportIncompatibleVariableOverride]
    settings: Settings  # pyright: ignore [reportIncompatibleVariableOverride]
    extends: list[str]  # pyright: ignore [reportIncompatibleVariableOverride]

    @classmethod
    def from_blueprint(cls, bp: Blueprint) -> Self:
        bp_clone = deepcopy(bp)
        bp_clone.set_defaults()
        return cast(Self, bp_clone)

    @classmethod
    def expand(cls, bp: Blueprint, bp_path: Path, logger: logging.Logger) -> Self:
        """resolves and merges extended blueprints"""
        if not bp.extends or len(bp.extends) == 0:
            return cls.from_blueprint(bp)

        try:
            paths = bp.extended_paths(bp_path)
            for path in paths:
                if not path.exists() or not path.is_file():
                    raise FileNotFoundError(f"extended '{path}' does not exist")

            dclass = DataclassOps(Blueprint, load_func, dump_func)
            accumulated: dict = {}
            for path in paths:
                logger.debug(f"{bp_path} extends {path}")
                try:
                    extended = dclass.load(path)
                except (DaciteError, ValueError) as e:
                    logger.error(str(e))
                    raise VulpixError(f"invalid blueprint at '{path}'")
                expanded_extended = cls.expand(extended, path, logger)
                merge_dicts(dclass.to_dict(expanded_extended), accumulated)

            merge_dicts(dclass.to_dict(bp), accumulated)
            expanded_bp = dclass.from_dict(accumulated)
            return cls.from_blueprint(expanded_bp)
        except (DaciteError, ValueError, FileNotFoundError) as e:
            logger.error(str(e))
            raise VulpixError(f"invalid blueprint at '{bp_path}'")


def datafile(path: Path, logger: logging.Logger) -> DataclassFile:
    def handle_error(exc_type: type[Exception], exc_value: Exception) -> bool:
        if issubclass(exc_type, (yaml.YAMLError, DaciteError, FileNotFoundError)):
            logger.error(str(exc_value))
            raise VulpixError(f"invalid blueprint at '{path}'")
        return False

    return DataclassFile(
        path,
        dclass=Blueprint,
        on_error=handle_error,
        load_func=load_func,
        dump_func=dump_func,
    )
