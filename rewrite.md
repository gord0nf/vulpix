README.md
bootstrap.sh
bootstrap.ps1
pyproject.toml
docs/
src/vulpix/
    __init__.py - defines module metadata (version, environment variables)
	__main__.py	- wraps everything in a handler for VulpixError, then executes cli main()
	utils.py	  - shared utilities
	logging.py 	- logging (which is constant no matter if core or cli or whatever)
	core/
        config.py   - core configuration (low level version of blueprint), a dataclass
		dotfiles.py	- exports sync_dotfiles() which takes in directory
		tasks.py	  - task runner definition (no cli stuff, just log separation, multithreading, etc)
		managers/
			__base__.py - defines base ABC class for interfacing managers
			assert.py
			manual/
			apt/
			__init__.py - exports __base__ exports, creates a dict for manager id to manager class definition
    blueprint.py  - loads and expands blueprint config	
	cli.py 	      - cli interface for core (exports main())
	
