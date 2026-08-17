from log import main as logger


def run_subcommand(subcommand: str, args: list[str]):

    match subcommand:
        case None | "" | "clean" | "install" | "config" | "reinstall":
            from subcommands.main import main as subcommand_main
        case "replay":
            from subcommands.replay import main as subcommand_main
        case "dotfiles":
            from subcommands.dotfiles import main as subcommand_main
        case "edit":
            from subcommands.edit import main as subcommand_main
        case "bootstrap":
            from subcommands.bootstrap import main as subcommand_main
        case _:
            logger.critical(f"invalid subcommand: {subcommand}")
            raise SystemExit(1)

    subcommand_main(subcommand, args)
