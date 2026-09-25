"""
NOTE: seperate from core/blueprint.py which has all the data struct definitions; this has logic to
parse blueprint yaml.
"""

import os
import sys
import dacite
import yaml
from pathlib import Path

from vulpix.core import VulpixError
from vulpix.cli import logging
from vulpix.core.blueprint import Blueprint

dacite_config = dacite.Config(strict=True)

# https://stackoverflow.com/a/20666342
def _merge(source: dict, destination: dict) -> dict:
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            _merge(value, node)
        else:
            destination[key] = value
    return destination

def get_extended_path(value: str, parent_dir: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = parent_dir / path
    if not path.exists():
        raise SchemaError("extended path does not exist: %s" % (path,))
    return path

def expand_blueprint(path: Path, logger: logging.Logger) -> tuple[dict, Blueprint]:
    """returns both raw dict and processes Blueprint object."""

    logger.debug(f"expanding blueprint at {path}")

    with open(path, "r") as file:
        blueprint_dict = yaml.safe_load(file)
    if blueprint_dict is None:
        blueprint_dict = {}

    extends: list[str] = []
    if "extends" in blueprint_dict:
        extends = blueprint_dict.pop("extends")
        if not isinstance(extends, list[str]):
            raise VulpixError(f"invalid 'extends' key in '{path}' (should be list of paths)")

    accumulated = {}
    for extended in extends:
        logger.debug(f"{path} extends {extended_path}")
        extended_path = get_extended_path(extended, path.parent)
        extended_blueprint, _ = expand_blueprint(extended_path, logger)
        _merge(extended_blueprint, accumulated)

    blueprint_dict = _merge(blueprint_dict, accumulated)

    # make sure its a valid blueprint
    try:
        blueprint = dacite.from_dict(
            data_class=Blueprint,
            data=blueprint_dict,
            config=dacite_config
        )
    except (dacite.DaciteError, ValueError) as e:
        logger.error(str(e))
        raise VulpixError(f"invalid blueprint at '{path}'")

    return blueprint_dict, blueprint
