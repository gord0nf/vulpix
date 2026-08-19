import os
from pathlib import Path
import shutil

import env, shell
from log import FatalCliError, main as logger


def install_fonts(fontdir: Path):
    match env.OS:
        case "windows":
            pass  # TODO
        case "linux":
            env.FONT_INSTALL.mkdir(parents=True, exist_ok=True)
            shell.safe_copy_merge(fontdir, env.FONT_INSTALL)
            shell.recursive_chmod(env.FONT_INSTALL, file_mode=0o644, dir_mode=0o755)
            if shutil.which("fc-cache") is not None:
                shell.RunCommand(["fc-cache"], logger=logger)


def setup_dotfiles(dotfiles: Path):
    ignore_file = dotfiles / ".vulpixignore"
    font_dir = dotfiles / "fonts"

    # get ignored paths
    ignored_paths = [ignore_file, font_dir]
    if ignore_file.exists():
        with open(ignore_file, "r") as f:
            for line in f:
                ignored_paths.append(dotfiles.joinpath(line))
    ignored_paths = [i for i in ignored_paths if i.exists()]

    logger.debug(f"ignoring: {ignored_paths}")

    # compile link map
    links: dict[Path, Path] = {}  # like [target_path]=link_path
    for item in dotfiles.iterdir():
        if any(item.samefile(i) for i in ignored_paths):
            continue
        if item.is_dir() and item.name == ".config":
            for tool in item.iterdir():
                if any(tool.samefile(i) for i in ignored_paths):
                    continue
                links[tool] = Path.home() / ".config" / tool.name
            continue

        links[item] = Path.home() / item.name

    logger.debug(f"links: {links}")

    # make sure we're not overwritting anything
    existing_items: list[Path] = []
    for target, link in links.items():
        if link.exists() and link.samefile(target):
            logger.debug(f"removing existing link: {link}")
            link.unlink()
        if link.exists():
            existing_items.append(link)
    if len(existing_items) > 0:
        print(
            "The following items will be overwritting and replaced by links:\n"
            + "\n".join(["  - " + str(i) for i in existing_items])
            + "\n"
        )
        if not shell.verify("Are you sure you want to continue?") or not shell.verify(
            "All these items will be deleted..."
        ):
            raise FatalCliError("aborted")
        for item in existing_items:
            os.remove(item)
        print()  # style

    raise SystemExit(1)

    # apply symlinks
    if len(links) > 0:

        for target, link in links.items():
            # _print_pretty_link "$item"
            link.symlink_to(target)
    else:
        logger.info("nothing to symlink")

    # install fonts
    if font_dir.exists():
        print()  # style
        logger.info(f"installing fonts from '{font_dir}'")
        install_fonts(font_dir)


def main(_: str, args: list[str]):
    dotfiles_path: Path | None = None
    match len(args):
        case 0:
            pass
        case 1:
            dotfiles_path = Path(args[0])
        case _:
            raise FatalCliError("invalid number of args")
    if not dotfiles_path:
        raise FatalCliError("please specify dotfiles dir in args or blueprint")

    logger.debug(f"dotfiles: {dotfiles_path}")
    setup_dotfiles(Path(dotfiles_path))
