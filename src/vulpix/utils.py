import os
import stat
import shutil
import threading
import subprocess
from logging import Logger
from pathlib import Path

from vulpix.core import env

def command_exists(command: str) -> bool:
    return shutil.which(command) is not None

def is_junction(path: Path) -> bool:
    if env.OS != 'windows' or not path.is_dir():
        return False
    if not (os.lstat(path).st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT):
        return False
    return not path.is_symlink()

def create_junction(target: Path, link: Path):
    cmd = ['mklink', '/j', os.fsdecode(str(link.resolve())), os.fsdecode(str(target.resolve()))]
    proc = subprocess.run(cmd, shell=True, capture_output=True)
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

def link(target: Path, link: Path, logger: Logger):
    """try symlink, else hardlink"""

    # symlink
    try: 
        link.symlink_to(target, target_is_directory=target.is_dir())
        return
    except OSError as e:
        logger.debug("symlink failed", exc_info=True)
        logger.warning("symlink failed. defaulting to hardlink/junction.")

    # hard link or junction
    if env.OS == 'windows' and target.is_dir():
        create_junction(target, link)
    else:
        link.hardlink_to(target)

def rm_link(link: Path):
    if env.OS == 'windows' and link.is_dir():
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
            copytree_windows(source, dest) # slower
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
            raise Exception('_atomic_change_start sanity check failed!')
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
                raise Exception('_atomic_change_apply sanity check failed!!')
            rm_fr(self.target)
            self.tmp.rename(self.target)

# https://gist.github.com/rene-d/9e584a7dd2935d0f461904b9f2950007
class Colors:
    BLACK = "\033[0;30m"
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    BROWN = "\033[0;33m"
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"
    CYAN = "\033[0;36m"
    LIGHT_GRAY = "\033[0;37m"
    DARK_GRAY = "\033[1;30m"
    LIGHT_RED = "\033[1;31m"
    LIGHT_GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    LIGHT_BLUE = "\033[1;34m"
    LIGHT_PURPLE = "\033[1;35m"
    LIGHT_CYAN = "\033[1;36m"
    LIGHT_WHITE = "\033[1;37m"
    BOLD = "\033[1m"
    FAINT = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    NEGATIVE = "\033[7m"
    CROSSED = "\033[9m"
    RESET = "\033[0m"

    # cancel SGR codes if we don't write to a terminal
    if not __import__("sys").stdout.isatty():
        for _ in dir():
            if isinstance(_, str) and _[0] != "_":
                locals()[_] = ""
    else:
        # set Windows console in VT mode
        if __import__("platform").system() == "Windows":
            kernel32 = __import__("ctypes").windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            del kernel32

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
