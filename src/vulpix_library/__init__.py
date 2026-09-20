import types
import importlib
import importlib.util

def check_package(package: str, manager: str) -> bool:
    return importlib.util.find_spec(f"{__name__}.{package}.{manager}") is not None

def get_package(package: str, manager: str) -> types.ModuleType | None:
    try:
        module = importlib.import_module(f".{package}.{manager}", package=__name__)
    except ModuleNotFoundError:
        return None
    return module
