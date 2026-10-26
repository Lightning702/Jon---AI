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
os.environ["JON_ZEIT_STUMM"] = "1"
os.environ["JON_SCHLUESSELSPEICHER"] = "datei"
os.environ["JON_KEIN_TERMINAL_BEFEHL"] = "1"

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


import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "standard: Test läuft mit der kostenlosen Standard-Stufe")


@pytest.fixture(autouse=True)
def _premium_stufe(request, monkeypatch):
    if request.node.get_closest_marker("standard"):
        return
    from app.services.premium import Premium

    monkeypatch.setattr(Premium, "stufe", lambda self: "admin")


@pytest.fixture(autouse=True)
def _agenten_ordner_im_testverzeichnis(monkeypatch):
    from app.services.agenten_service import AgentenService

    monkeypatch.setattr(AgentenService, "standard_ordner", staticmethod(lambda: _TEST_DATA_DIR / "Jon Agenten"))


@pytest.fixture(autouse=True)
def _jon_ordner_im_testverzeichnis(monkeypatch, tmp_path_factory):
    from app.services import dateiraum_service

    monkeypatch.setattr(dateiraum_service, "_service", None)
    ordner = tmp_path_factory.mktemp("jon-ordner") / "Jon"
    monkeypatch.setattr(dateiraum_service.DateiraumService, "wurzel", lambda self: ordner)
    heim = ordner.parent / "heim"
    for name in ("Desktop", "Documents", "Downloads", "Pictures", "Videos", "Music"):
        (heim / name).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(dateiraum_service, "_heim", lambda: heim)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: heim))


ECHTER_JON = ("127.0.0.1:8756", "localhost:8756")


@pytest.fixture(autouse=True)
def _nie_den_echten_jon_anfunken(monkeypatch):
    import httpx

    echt_post = httpx.post
    echt_senden = httpx.Client.send

    def gesperrt(url) -> bool:
        return any(adresse in str(url) for adresse in ECHTER_JON)

    def post(url, *args, **kwargs):
        if gesperrt(url):
            raise httpx.ConnectError(f"Tests duerfen den laufenden Jon nicht ansprechen: {url}")
        return echt_post(url, *args, **kwargs)

    def senden(self, request, *args, **kwargs):
        if gesperrt(request.url):
            raise httpx.ConnectError(f"Tests duerfen den laufenden Jon nicht ansprechen: {request.url}")
        return echt_senden(self, request, *args, **kwargs)

    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setattr(httpx.Client, "send", senden)
    from app.codeserver import Codeserver

    monkeypatch.setattr(Codeserver, "_jon_aufruf", lambda self, pfad, daten: False)
