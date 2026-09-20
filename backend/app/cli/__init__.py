from __future__ import annotations

import asyncio
import os
import sys

from app.core.fehler import leise


def _konsole_vorbereiten() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception as fehler:
        leise(fehler, "cli")
    if sys.platform == "win32":
        try:
            import ctypes

            kernel = ctypes.windll.kernel32
            kernel.SetConsoleMode(kernel.GetStdHandle(-11), 7)
        except Exception as fehler:
            leise(fehler, "cli")
            os.system("")


def main(argv: list[str] | None = None) -> None:
    _konsole_vorbereiten()
    args = list(argv if argv is not None else sys.argv[1:])
    modus = ""
    if args and args[0].lower() in ("code", "chat"):
        modus = args.pop(0).lower()
    from app.cli.sitzung import JonTerminal

    terminal = JonTerminal(modus)
    if args:
        frage = " ".join(args)
        try:
            asyncio.run(terminal._runde(frage))
        except KeyboardInterrupt:
            pass
        return
    try:
        asyncio.run(terminal.laufen())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
