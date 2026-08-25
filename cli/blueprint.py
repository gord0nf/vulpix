import os
from pathlib import Path
import sys
import yaml
from schema import Optional, Regex, Schema, SchemaError, Use

import env


def _get_extended_path(value: str, parent_dir: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = parent_dir / path
    if not path.exists():
        raise SchemaError("extended path does not exist: %s" % (path,))
    return path


_cpu_count = os.cpu_count()

SCHEMA = Schema(
    {
        "extends": Optional(
            [Use(lambda e: _get_extended_path(e, env.BLUEPRINT_PATH.parent))], []
        ),
        "packages": [
            Regex(
                r"^[A-Za-z]+@[A-Za-z]+$",
                error="invalid package syntax (should be name@manager)",
            )
        ],
        "config": object,
        "dotfiles": Optional(str, None),
        "settings": Optional(
            {
                "threads": Optional(int, _cpu_count + 4 if _cpu_count else 4),
                "alt_screen": Optional(bool, True),
                "abort_uninstall_threshold": Optional(int, 10),
                "apt_mode": Optional(Regex(r"^(safe|strict)$"), "safe"),
            }
        ),
    }
)

# follow 'extends' to create expand_blueprint -----------------------------------------------------


# https://stackoverflow.com/a/20666342
def _merge(source: dict, destination: dict) -> dict:
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            _merge(value, node)
        else:
            destination[key] = value
    return destination


def expand_blueprint(path: Path) -> dict:
    with open(path, "r") as file:
        blueprint = yaml.safe_load(file)
    blueprint = SCHEMA.validate(blueprint)

    accumulated = {}
    for extended_path in blueprint["extends"]:
        extended_blueprint = expand_blueprint(extended_path)
        _merge(extended_blueprint, accumulated)

    return _merge(blueprint, accumulated)


try:
    # main exports
    expanded_blueprint = expand_blueprint(env.BLUEPRINT_PATH)
    expanded_blueprint_path = env.DATA_PATH / "expanded_blueprint.yaml"
    with open(expanded_blueprint_path, "w") as f:
        yaml.safe_dump(expanded_blueprint, f)
except SchemaError as e:
    sys.exit(e.code)  # https://github.com/keleshev/schema#user-friendly-error-reporting
