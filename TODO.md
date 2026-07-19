- general
    - add software things as needed
    - bsh/zsh/powershell/pwsh
        - option to manually disable external tools (like omp) in yml
- v1.0: initial vulpix
    - vulpix = platform agnostic manager for install managers
        - key concepts:
            - cross-os/platform/manager config-driven software setup manager
            - blueprint = yaml config that defines what to install and how to configure
                - meant to be atomic and config-driven
                - cache for downloaded things that are removed from config
            - dotfiles = define _your_ posix-like dot-files repo and apply with manager/os
              abstracted
    - custom configuration is meant to be stored in your very own git repo:
        - repo should be formatted like a "dot-files" repo
            - in fact, the whole purpose is so that if you don't wanna use vulpix you can just clone
              the repo into user home, just like dot-files
        - cloned git repo stored in vulpix data dir and `vuplix apply` to copy/symlink config to the
          correct locations
            - recommended practice: only define committed config in XDG*CONFIG_HOME dirs and define
              machine-specific config to actual dot \_files* in root user home. this way you can
              edit your custom config in the normal locations without ever needing to run
              `vulpix apply`. on linux, you wouldn't need to do this anyway because vulpix creates
              both file and directory symlinks. but for _windows_, file links are only possible for
              with admin, so if you're a normal user, you would have to run `vulpix apply` every
              time you edit a config file not in a symlinked directory (usually the root dot files).
    - make like a good little cli
        - tee stdout to log file
        - clear screen after each thing
        - better documentation (README, etc)
        - (maybe) shell completion for things
        - check if dir link is the right dir link instead of asking to replace every time
        - standardiz XDG stuff and make sure dirs exist
    - basic windows compat
        - `win-bootstrap.ps1` option to use Git Bash or wsl
            - maybe move win-bootstrap as standard manual install script location for git
        - `setup.ps1` in root that runs bootstrap if bash doesn't exist
- v1.1: windows compatiblity
    - vulpix wsl support
    - make v2 setup compatible with windows
        - psmux
        - btop4win
        - docker
        - mpd
        - yt-dlp
        - fzf? (but pwsh already has smth like it...)
        - mpv equivalent for windows? (necessary?)
    - (maybe) load .env into windows system env
