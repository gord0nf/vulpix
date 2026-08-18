from log import main as logger


class PackageManagement:
    def __init__(self) -> None:
        pass


class PackageConfiguration:
    def __init__(self) -> None:
        pass


def main(subcommand: str, scope_packages: list[str]):
    if not subcommand:
        subcommand = "clean install config"

    clean = False
    install = False
    reinstall_instead_of_update = False
    config = False
    config_packages = False
