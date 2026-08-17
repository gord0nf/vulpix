# package install library

```
library/
├─ packages/
│  ├─ ${package}/
│  │  └─ ...install script for each supported manager (e.g. apt.sh)
│  └─ ...other packages
└─ managers/
   ├─ ${manager}/
   │  ├─ interface.sh
   │  └─ ...any other utils or docs
   └─ ...other managers
```
