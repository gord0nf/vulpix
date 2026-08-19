import logging
import os
import shutil
import subprocess
from pathlib import Path


def safe_copy_merge(src: Path, dst: Path):
    def copy_without_overwrite(src, dst):
        if not os.path.exists(dst):
            shutil.copy2(src, dst)

    shutil.copytree(src, dst, dirs_exist_ok=True, copy_function=copy_without_overwrite)


def recursive_chmod(dir, file_mode=0o644, dir_mode=0o755):
    for root, dirs, files in os.walk(dir):
        for d in dirs:
            os.chmod(os.path.join(root, d), dir_mode)
        for f in files:
            os.chmod(os.path.join(root, f), file_mode)


def verify(prompt: str) -> bool:
    return input(prompt + " (y/n): ").lower().strip().startswith("y")


# https://jon.sprig.gs/blog/post/8025
class RunCommand:
    command = ""
    cwd = ""
    running_env = {}
    stdout = []
    stderr = []
    exit_code = 999

    def __init__(
        self,
        command: list = [],
        cwd: str | None = None,
        env: dict | None = None,
        raise_on_error: bool = True,
        logger: logging.Logger | None = None,
    ):
        self.command = command
        self.cwd = cwd

        self.running_env = os.environ.copy()

        if env is not None and len(env) > 0:
            for env_item in env.keys():
                self.running_env[env_item] = env[env_item]

        if logger:
            logger.debug(f'exec: {" ".join(command)}')

        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True,
                env=self.running_env,
            )
            # Store the result because it worked just fine!
            self.exit_code = 0
            self.stdout = result.stdout.splitlines()
            self.stderr = result.stderr.splitlines()
        except subprocess.CalledProcessError as e:
            # Or store the result from the exception(!)
            self.exit_code = e.returncode
            self.stdout = e.stdout.splitlines()
            self.stderr = e.stderr.splitlines()

        # If verbose mode is on, output the results and errors from the command execution
        if len(self.stdout) > 0 and logger:
            logger.debug(f"stdout: {"\n".join(self.stdout)}")
        if len(self.stderr) > 0 and logger:
            logger.debug(f"stderr: {"\n".join(self.stderr)}")

        # If it failed and we want to raise an exception on failure, record the command and args
        # then Raise Away!
        if raise_on_error and self.exit_code > 0:
            raise Exception(
                f"Error ({self.exit_code}) running command: {command}\nstderr: {self.stderr}\nstdout: {self.stdout}"
            )

    def __repr__(self) -> str:  # Return a string representation of this class
        return "\n".join(
            [
                f"Command: {self.command}",
                f"Directory: {self.cwd if not None else '{current directory}'}",
                f"Env: {self.running_env}",
                f"Exit Code: {self.exit_code}",
                f"nstdout: {self.stdout}",
                f"stderr: {self.stderr}",
            ]
        )


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
