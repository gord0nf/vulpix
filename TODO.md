# TODO list

- v2.0: python rewrite
    - rewrite in python because the codebase was getting to big/complex
        - multiprocessing in bash is horrible and not very performant
        - bash on windows (both with mingw and cygwin) either doesn't work becuase no flock or is
          super slow because of how tasks work
    - no yq dep (instead use pyyaml)
    - better cli
- v2.1: windows compatiblity
    - actually make sure v1.0 features work on windows
    - replace windows bash bootstrap (originally through Git for Windows/Mingw) with MSYS2
    - new windows-specific manual packages
        - windows_powershell
        - powertoys
        - winterm
        - psmux
        - btop4win
        - mpv (for both windows and linux)
- v2.2: package managers for windows
    - add pacman manager (primarily for msys2, but also for arch linux)
    - add winget manager

## unversioned/general

- shell completion for subcommands, packages, etc
