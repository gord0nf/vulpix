from collections.abc import Callable
from dataclasses import dataclass, field

from vulpix.core import logging


@dataclass
class Template:
    all_binaries: list[str] = field(default_factory=list)
    some_binaries: list[list[str]] = field(default_factory=list)
    check: Callable[[logging.Logger], bool] | None = None


templates: dict[str, Template] = {
    "python": Template(
        some_binaries=[
            ["python", "python3", "py"],
            ["pip", "pip3"],
        ]
    ),
}
