from log import main as logger

class SetupRunner:
    clean: bool = False
    install: bool = False
    reinstall_instead_of_update: bool = False
    config: bool = False
    config_packages = False

    _blueprint_packages: dict[str, list[str]] # packages by manager
    _scope_packages: dict[str, list[str]] # packages by manager

    def __init__(self):
        from blueprint import extended_blueprint as blueprint
        self._blueprint_packages = packages_by_manager(blueprint.packages)
        logger.debug(f"got blueprint packages: {self._blueprint_packages}")

    @scope_packages.setter
    def scope_packages(self, scope_packages: list[str]):
        if len(scope_packages) == 0:
            self._scope_packages = self._blueprint_packages
        else:
            self._scope_packages = packages_by_manager(scope_packages)

            for manager, packages in self._scope_packages:
                blueprint_packages = self._blueprint_packages.
                for package in packages:
    

def main(subcommand: str, args: list[str]):
    setup = SetupRunner()

    if not subcommand:
        subcommand = 'clean install config'
