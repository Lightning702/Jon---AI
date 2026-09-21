from __future__ import annotations

import os
import sys


CLI_WOERTER = ("cli", "terminal", "jon")


def main() -> None:
    if getattr(sys, "frozen", False):
        os.chdir(os.path.dirname(sys.executable))

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
