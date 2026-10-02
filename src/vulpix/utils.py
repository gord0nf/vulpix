import inspect
import os
import shutil
import stat
import subprocess
import threading
from pathlib import Path

from vulpix.core import VulpixError, logging, system

# file system utils -------------------------------------------------------------------------------


def is_junction(path: Path) -> bool:
    if system.OS != "windows" or not path.is_dir():
        return False
    if not (os.lstat(path).st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT):
        return False
    return not path.is_symlink()


def create_junction(target: Path, link: Path):
    cmd = [
        "mklink",
        "/j",
        os.fsdecode(str(link.resolve())),
        os.fsdecode(str(target.resolve())),
    ]
    proc = subprocess.run(cmd, shell=True, capture_output=True, check=False)
    if proc.returncode:
        raise OSError(proc.stderr.decode().strip())


def rm_junction(link: Path):
    os.rmdir(link)


def copytree_windows(src: Path, dst: Path):
    """copytree but preserves ntfs junctions"""

    if not src.is_dir():
        raise NotADirectoryError(src)
    if dst.exists():
        raise FileExistsError(dst)
    dst.mkdir(parents=True)

    for entry in os.scandir(src):
        src_path = Path(entry.path)
        dst_path = dst / entry.name

        if is_junction(src_path):
            target = Path(os.path.realpath(src_path))
            create_junction(target, dst_path)
        elif entry.is_dir(follow_symlinks=False):
            copytree_windows(src_path, dst_path)
        else:
            shutil.copy2(src_path, dst_path, follow_symlinks=False)


def link(target: Path, link: Path, logger: logging.Logger):
    """try symlink, else hardlink"""

    # symlink
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
        return
    except OSError:
        logger.debug("symlink failed", exc_info=True)
        logger.warning("symlink failed. defaulting to hardlink/junction.")

    # hard link or junction
    if system.OS == "windows" and target.is_dir():
        create_junction(target, link)
    else:
        link.hardlink_to(target)


def rm_link(link: Path):
    if system.OS == "windows" and link.is_dir():
        rm_junction(link)
    else:
        link.unlink()


def rm_fr(path: Path):
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)


def cp_r(source: Path, dest: Path, preserve_junctions: bool = False):
    if source.is_dir():
        if preserve_junctions:
            copytree_windows(source, dest)  # slower
        else:
            shutil.copytree(source, dest)
    else:
        shutil.copy2(source, dest, follow_symlinks=False)


class AtomicChange:
    target: Path
    tmp: Path
    preserve_junctions: bool

    def __init__(self, target: Path, preserve_junctions: bool = False):
        self.target = target
        self.tmp = target.with_suffix(".tmp")
        self.preserve_junctions = preserve_junctions

    def __enter__(self):
        if self.tmp.exists():
            raise FileExistsError("_atomic_change_start sanity check failed!")
        if self.target.exists():
            cp_r(self.target, self.tmp, self.preserve_junctions)
        return self.tmp

    def __exit__(self, exc_type, *_):
        if exc_type is not None:
            # abort
            rm_fr(self.tmp)
            return False
        else:
            # apply
            if not self.tmp.exists():
                raise FileNotFoundError("_atomic_change_apply sanity check failed!!")
            rm_fr(self.target)
            self.tmp.rename(self.target)


# shell utils -------------------------------------------------------------------------------------


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def run_cmd(
    *cmd: str, logger: logging.Logger, return_stdout: bool = False
) -> list[str] | None:
    logger.debug(f"running external cmd: {cmd}")
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if process.stderr:
        for line in process.stderr:
            logger.info(line.strip())

    stdout, _ = process.communicate()
    if process.returncode != 0:
        raise VulpixError("external script failed")

    if stdout:
        return stdout.splitlines()
    return []


# misc utils --------------------------------------------------------------------------------------


class Broadcast:
    _event: threading.Event
    _lock: threading.Lock

    def __init__(self):
        self._event = threading.Event()
        self._lock = threading.Lock()

    def broadcast(self):
        with self._lock:
            self._event.set()
            self._event.clear()

    def wait(self):
        return self._event.wait()


def accepts_kwarg(func_sig: inspect.Signature, kwarg_name: str):
    if kwarg_name in func_sig.parameters:
        return func_sig.parameters[kwarg_name].kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )

    return any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in func_sig.parameters.values()
    )
