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
os.environ["JON_TOKEN"] = "test-token-fuer-die-testsuite"

from app.core.config import DATA_DIR
from app.db.database import init_db

if DATA_DIR.resolve() != _TEST_DATA_DIR.resolve():
    raise RuntimeError(
        f"Tests würden in echte Nutzerdaten schreiben: {DATA_DIR}. "
        "JON_DATA_DIR muss vor dem Import von app.core.config gesetzt sein."
    )

init_db()

from fastapi.testclient import TestClient as _TestClient

_original_init = _TestClient.__init__


def _init_with_token(self, *args, **kwargs):
    if kwargs.get("headers") is None:
        kwargs["headers"] = {"X-Jon-Token": os.environ["JON_TOKEN"]}
    _original_init(self, *args, **kwargs)


_TestClient.__init__ = _init_with_token
