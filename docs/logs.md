# logs

logs are stored in the following locations depending on where you're running vulpix and under what
user:

- linux, root: `/var/log/vulpix`
- linux, user: `${XDG_STATE_HOME:-$HOME/.local/state}/vulpix/log`
- windows, root: `$ProgramData\vulpix\log`
- windows, user: `$LOCALAPPDATA\vulpix\log`

log directory structure:

```
log/
├─ tasks/
│  ├─ ${taskname}.log
│  └─ ...
└─ main.log
```

logs are cleared every time vulpix is ran.
