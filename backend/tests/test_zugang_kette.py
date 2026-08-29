from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.core import auth
from app.main import app

client = TestClient(app)

ELECTRON = Path(__file__).resolve().parents[2] / "frontend" / "electron"
WEB = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib"


def lies(pfad: Path) -> str:
    return pfad.read_text(encoding="utf-8")


def test_health_nennt_die_schluesseldatei():
    daten = client.get("/api/health").json()
    assert daten["token_file"]
    assert daten["token_file"].endswith("access.token")


def test_gemeldete_datei_enthaelt_den_wirksamen_schluessel(tmp_path, monkeypatch):
    ziel = tmp_path / "access.token"
    monkeypatch.setattr(auth, "TOKEN_FILE", ziel)
    monkeypatch.setattr(auth, "_cached", None)
    monkeypatch.setenv("JON_TOKEN", "schluessel-aus-der-umgebung")

    wirksam = auth.get_token()

    assert wirksam == "schluessel-aus-der-umgebung"
    assert ziel.exists()
    assert ziel.read_text(encoding="utf-8").strip() == wirksam


def test_neuer_schluessel_landet_auch_in_der_datei(tmp_path, monkeypatch):
    ziel = tmp_path / "access.token"
    monkeypatch.setattr(auth, "TOKEN_FILE", ziel)
    monkeypatch.setattr(auth, "_cached", None)
    monkeypatch.delenv("JON_TOKEN", raising=False)

    erster = auth.get_token()
    zweiter = auth.reset_token()

    assert zweiter != erster
    assert ziel.read_text(encoding="utf-8").strip() == zweiter

    monkeypatch.setattr(auth, "_cached", None)
    monkeypatch.setenv("JON_TOKEN", os.environ.get("JON_TOKEN", "test-token"))


def test_preload_reicht_den_schluessel_an_die_app_weiter():
    quelle = lies(ELECTRON / "preload.cjs")
    assert "--jon-token=" in quelle
    assert "token: jonToken" in quelle
    assert 'ipcRenderer.invoke("auth:token")' in quelle
    assert 'ipcRenderer.on("jon:token"' in quelle


def test_hauptprozess_beantwortet_die_nachfrage():
    quelle = lies(ELECTRON / "main.cjs")
    assert 'ipcMain.handle("auth:token"' in quelle
    assert "async function refreshToken()" in quelle
    assert "token_file" in quelle
    assert "additionalArguments: tokenArgs()" in quelle


def test_jedes_fenster_bekommt_den_schluessel():
    quelle = lies(ELECTRON / "main.cjs")
    assert quelle.count("additionalArguments: tokenArgs()") == quelle.count(
        "contextIsolation: true"
    )


def test_nebenfenster_koennen_nachfragen():
    for name in ("petPreload", "quickaskPreload", "quickwritePreload", "privatePreload"):
        quelle = lies(ELECTRON / f"{name}.cjs")
        assert "jonToken" in quelle, name
        assert "jonTokenHolen" in quelle, name


def test_app_wiederholt_nach_einer_abweisung():
    quelle = lies(WEB / "token.ts")
    assert "antwort.status !== 401" in quelle
    assert "tokenNachfragen" in quelle
    assert "onToken" in quelle


def test_kleine_fenster_wiederholen_ebenfalls():
    for name in ("pet.html", "quickask.html"):
        quelle = lies(ELECTRON / name)
        assert "X-Jon-Token" in quelle, name
        assert "jonTokenHolen" in quelle, name


def test_hauptprozess_ruft_die_api_nur_mit_schluessel():
    quelle = lies(ELECTRON / "main.cjs")
    assert "async function apiFetch(" in quelle
    roh = [
        zeile.strip()
        for zeile in quelle.splitlines()
        if "fetch(`${API_BASE}" in zeile
    ]
    assert len(roh) == 1, roh
    assert "/health" in roh[0]
