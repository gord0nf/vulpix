# package install library

```
library/
├─ packages/
│  ├─ $PACKAGE/
│  │  └─ ...install script for each supported manager (e.g. apt.sh)
│  └─ ...other packages
└─ managers/
   └─ ...script for each manager (e.g. apt.sh) to sync blueprint with install manager
```
