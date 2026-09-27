from __future__ import annotations

import os
import sys


CLI_WOERTER = ("cli", "terminal", "jon")
EINRICHT_WOERTER = ("terminal-einrichten", "terminal-entfernen")


def main() -> None:
    if getattr(sys, "frozen", False):
        os.chdir(os.path.dirname(sys.executable))

    if len(sys.argv) > 1 and sys.argv[1].lower() in EINRICHT_WOERTER:
        from app.services import terminal_service

        if sys.argv[1].lower() == "terminal-entfernen":
            ergebnis = terminal_service.entfernen()
        else:
            ergebnis = terminal_service.einrichten()
        print(ergebnis.get("error") or ergebnis.get("befehl") or "ok")
        sys.exit(1 if ergebnis.get("error") else 0)

    if len(sys.argv) > 1 and sys.argv[1].lower() in CLI_WOERTER:
        from app.cli import main as cli_main

        cli_main(sys.argv[2:])
        return

    import uvicorn

    from app.core.config import get_settings
    from app.main import _free_port, app

    settings = get_settings()
    host = "0.0.0.0" if settings.jon_lan else settings.host
    _free_port(settings.host, settings.port)
    uvicorn.run(app, host=host, port=settings.port, reload=False)


if __name__ == "__main__":
    main()
