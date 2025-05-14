from task import EpubBulider
from env import Config, TUI


def main():
    config = Config(
        targ=".",
        cache="./!!!Backups",
        utils="./Utils",
        sync="C:/Users/BeetSoup/OneDrive/!Novel"
    )
    tui = TUI()
    finalPaths = []
    for p in config.findall():
        tui.Display.Temp(f"Found {p}")
        EpubBulider(p, config, tui).run()
        try:
            tui.Display.Temp(f"Converted {p}")
            finalPaths.append(p)
        except BaseException as e:
            tui.Display.Temp(f"Error converting {p}: {e}")
            tui.input("Press Enter to continue...")
    tui.clearAll()
    tui.add("[red]=All works has done=",
            f"[blue]Books[green]{finalPaths}[blue]try to backup or sync.")
    tui.Display.Temp(f"[red]Backup towards [green]{config.cache}")
    if config.isSync():
        if tui.input(
                f"[red]Syncing towards [green]{config.sync}\n[red]Press [blue]y[red] to continue:").strip() == "y":
            config.Sync(finalPaths)
            config.Backup(finalPaths)
    else:
        if tui.input(f"[red]Press [blue]y[red] to continue:").strip() == "y":
            config.Backup(finalPaths)
    tui.exitWithin3S()


if __name__ == "__main__":
    main()
