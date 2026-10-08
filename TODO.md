# TODO list

- v2.0: python rewrite
    - refactor:
        - rewrite in python because the codebase was getting to big/complex
            - multiprocessing in bash is horrible and not very performant
            - bash on windows (both with mingw and cygwin) either doesn't work becuase no flock or is
              super slow because of how tasks work
        - multithreaded task queue for tasks
        - no yq dep (instead use pyyaml)
        - better cli
    - feats:
        - plugin-based package management
        - plugin-based config management
        - bootstrap by installing python and just installing vulpix w/ pip
        - dotenv subcommand to allow sourcing vulpix .env file
        - cross-platform dotfiles
- v2.2: general manual packages & unix feats
    - new manual packages
        - bash
        - git
        - golang
        - gradle
        - java
        - neovim
        - nodejs
        - ohmyposh
        - pwsh
        - python
        - ripgrep
        - rmpc
        - vim
        - ytdlp
        - fzf
    - add apt manager
- v2.2: windows feats
    - new windows-specific manual packages
        - msys2
        - windows_powershell
        - powertoys
        - winterm
        - psmux
        - btop4win
        - mpv (for both windows and linux)
    - add pacman manager (for arch linux and msys2; test on both)
    - add winget manager

## unversioned/general

- shell completion for subcommands, packages, etc
- publish to pypi
- have field in blueprint for required plugin packages?
