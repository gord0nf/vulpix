# managers

each manager is a module in the directory. managers get populated at runtime by cli by iterating
over this directory (modules starting in `_` are ignored).

the `PackageManager` class is defined in `__shared__.py`. each manager module is required to export
`Manager` which should be the class definition for a subclass of `PackageManager`.
