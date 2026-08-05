# managers

each manager has a subdirectory in this dir with one purpose. each subdirectory must implement a
`interface.sh` with one purpose: to export functions that allow the parent script to
install/uninstall/update/reinstall packages installed by the manager to reflect the blueprint.

each manager interface script should export the following functions (a "package" input or output is
a string corresponding to a dir name in `library/packages`, so some conversion to manager package
name might be required):

```bash
# Required.
#
# returns 0 if yes, else no
can_use_manager() {
    ...
}

# Required.
#
# returns 0 if yes, else no.
package_is_supported() {
    local package=$1
    ...
}

# Optional.
#
# runs once before install/uninstall loop (for any preprocessing like source updating, garbage collecting, etc.)
presetup() {
    ...
}

# Optional.
#
# runs once after install/uninstall loop (for any postprocessing like global cleanup, etc.)
postsetup() {
    ...
}

# Required.
#
# clears and writes to array of packages to `installed`
get_installed() {
    local -n installed=$1
    ...
}

# Required.
# returns 0 if success, 1 if general failure, 2 if some packages failed (should also rollback changes to make atomic)
install_packages() {
    local -n packages=$1
    ...
}

# Required.
# returns 0 if success, 1 if general failure, 2 if some packages failed (should also rollback changes to make atomic).
#
# also recommended: having a cache so it can be recovered easily (then actually removing them after period)
uninstall_packages() {
    local -n packages=$1
    ...
}

# Required.
# returns 0 if success, 1 if general failure, 2 if some packages failed (should also rollback changes to make atomic)
update_packages() {
    local -n packages=$1
    ...
}

# Required.
# returns 0 if success, 1 if general failure, 2 if some packages failed (should also rollback changes to make atomic)
#
# this can just be running `uninstall_packages ... && install_packages ...` but some managers
# have more complex or efficient reinstall mechanics (for example, uninstall/reinstall wouldn't
# work if manager implements cache, because we want a *clean* install)
reinstall_packages() {
    local -n packages=$1
    ...
}
```

but beyond that the implementation is up to the script. the parent script operates under the
assumption that these operations are atomic, so it doesn't attempt any cleanup on failure (or
success).
