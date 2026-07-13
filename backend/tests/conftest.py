from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_TEST_DATA_DIR = Path(tempfile.gettempdir()) / "jon-test-data"
shutil.rmtree(_TEST_DATA_DIR, ignore_errors=True)
_TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
os.environ["JON_DATA_DIR"] = str(_TEST_DATA_DIR)

from app.core.config import DATA_DIR
from app.db.database import init_db

if DATA_DIR.resolve() != _TEST_DATA_DIR.resolve():
    raise RuntimeError(
        f"Tests würden in echte Nutzerdaten schreiben: {DATA_DIR}. "
        "JON_DATA_DIR muss vor dem Import von app.core.config gesetzt sein."
    )

init_db()
