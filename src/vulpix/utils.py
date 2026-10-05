import inspect
import json
import os
import shutil
import stat
import subprocess
import threading
from collections.abc import Callable
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, ClassVar, Protocol, Self, TextIO

import dacite
from filelock import FileLock, Timeout

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


def is_executable(path: Path) -> bool:
    # TODO: better way to check if exec on windows?
    return system.OS != "windows" and path.is_file() and os.access(path, os.X_OK)


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


def path_as_salt(path: Path):
    return str(path).replace(":", "!").replace("/", "_").replace("\\", "_")


# shell utils -------------------------------------------------------------------------------------


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


class LoggedCommand:
    cmd: list[str]
    logger: logging.Logger

    stdout: list[str] | None = None
    stderr: list[str] | None = None

    def __init__(self, *cmd: str, logger: logging.Logger):
        self.cmd = list(cmd)
        self.logger = logger

    def run(self, log_stdout: bool = True) -> Self:
        if log_stdout:
            stdout_fd = subprocess.PIPE
            stderr_fd = subprocess.STDOUT
        else:
            stdout_fd = subprocess.PIPE
            stderr_fd = subprocess.PIPE

        p = subprocess.Popen(self.cmd, stdout=stdout_fd, stderr=stderr_fd, text=True)
        log_stream = p.stdout if log_stdout else p.stderr
        if log_stream:
            for line in log_stream:
                self.logger.info(line.strip())

        if p.returncode:
            raise VulpixError("external script failed")

        stdout, stderr = p.communicate()
        self.stdout = stdout.split("\n")
        self.stderr = stderr.split("\n")

        return self


# misc utils --------------------------------------------------------------------------------------


dacite_config = dacite.Config(
    strict=True, type_hooks={datetime: datetime.fromisoformat, date: date.fromisoformat}
)


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


class Dataclass(Protocol):
    """credit: https://stackoverflow.com/a/55240861"""

    __dataclass_fields__: ClassVar[dict[str, Any]]


def _asdict_no_underscores(data: list[tuple[str, Any]]) -> dict[str, Any]:
    return {k: v for k, v in data if not k.startswith("_")}


class DataclassFile[D: Dataclass]:
    """
    context manager that locks a file, reads and validates it into the target
    dataclass, then writes and released file on exit.

    IMPORTANT: the dataclass must have defaults/option fields if the file doesn't
    exist
    """

    type LoadFunction = Callable[[TextIO], dict]
    type DumpFunction = Callable[[dict, TextIO], None]
    type HandleException = Callable[[type[Exception], Exception], bool | None]

    path: Path
    lock: FileLock
    dclass_def: type[D]
    dclass_instance: D

    acquire_timeout: int = 10
    load_func: LoadFunction = staticmethod(json.load)
    dump_func: DumpFunction = staticmethod(
        lambda d, f: json.dump(d, f, default=str, indent=4)
    )
    on_error: HandleException | None

    def __init__(
        self, path: Path, dclass: type[D], on_error: HandleException | None = None
    ):
        self.path = path
        self.lock = FileLock(path.with_suffix(".lock"))
        self.dclass_def = dclass
        self.on_error = on_error

    def __enter__(self) -> D:
        try:
            self.lock.acquire(timeout=self.acquire_timeout)
        except Timeout:
            raise VulpixError(f"couldn't aquire lock for {self.path}")

        try:
            if self.path.exists() and self.path.stat().st_size > 0:
                with open(self.path, "r") as file:
                    d = self.load_func(file)
                self.dclass_instance = dacite.from_dict(
                    data_class=self.dclass_def, data=d, config=dacite_config
                )
            else:
                self.dclass_instance = self.dclass_def()
        except Exception as e:
            if not self.on_error or self.on_error(type(e), e) is False:
                raise

        return self.dclass_instance

    def __exit__(self, exc_type, *_):
        if exc_type is not None:
            self.lock.release()
            return False

        try:
            d = asdict(self.dclass_instance, dict_factory=_asdict_no_underscores)
            with open(self.path, "w") as file:
                self.dump_func(d, file)
        except Exception as e:
            if not self.on_error or self.on_error(type(e), e) is False:
                raise

        self.lock.release()

    def check(self):
        with self:
            pass


def accepts_kwarg(func_sig: inspect.Signature, kwarg_name: str):
    if kwarg_name in func_sig.parameters:
        return func_sig.parameters[kwarg_name].kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )

    return any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in func_sig.parameters.values()
    )
