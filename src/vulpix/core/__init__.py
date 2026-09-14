from logging import Logger

from vulpix import VulpixError
from vulpix.core import managers
from vulpix.core.blueprint import Blueprint

def apply(blueprint: Blueprint, logger: Logger):
    manager_instances: dict[str, managers.PackageManager] = {}

    for manager_id, packages in blueprint.packages.items():
        if manager_id not in managers.definition_by_id:
            raise VulpixError(f"invalid manager '{manager_id}'")
        try:
            manager = managers.definition_by_id[manager_id]()
            manager.check_packages(packages)
            manager_instances[manager_id] = manager
        except managers.ManagerUnsupported as e:
            raise VulpixError(f"the '{e.manager}' manager cannot be used on your system: {e.message}")
        except managers.InvalidPackage as e:
            raise VulpixError(f"the '{e.package}' is not supported by '{e.manager}' manager")

    for manager_id, manager in manager_instances.items():
        blueprint_packages = blueprint.packages[manager_id]
        installed_packages = manager.get_installed()
        logger.debug(f"manager={manager_id}, blueprint={blueprint_packages}, installed={installed_packages}")

        for package in blueprint_packages:
            if package in installed_packages:
                manager.update_packages.append(package)
            else:
                manager.install_packages.append(package)
        for package in installed_packages:
            if package not in blueprint_packages:
                manager.uninstall_packages.append(package)

        logger.debug(str(manager))
        manager.run(logger)
