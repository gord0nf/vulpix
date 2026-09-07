README.md
bootstrap.sh
bootstrap.ps1
pyproject.toml
docs/
src/vulpix/
    __init__.py - defines module metadata (version, environment variables)
	__main__.py	- wraps everything in a handler for VulpixError, then executes cli main()
	utils.py	  - shared utilities
	core/
        __init__.py - exports apply() which orchestrates all package management/configuration and dotfiles
        config.py   - core configuration (low level version of blueprint), a dataclass
        logging.py 	- logging (which is constant no matter if core or cli or whatever)
		tasks.py	  - task runner definition (no cli stuff, just log separation, multithreading, etc)
		managers/
			__base__.py - defines base ABC class for interfacing managers
			assert.py
			manual/
			apt/
			__init__.py - exports __base__ exports, creates a dict for manager id to manager class definition
		dotfiles.py	- exports sync_dotfiles() which takes in directory
    blueprint.py  - loads and expands blueprint config	
	cli.py        - defines main() entrypoint for cli with arg parsing, subcommands
