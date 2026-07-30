from __future__ import annotations

import asyncio
import http.server
import json
import os
import socketserver
import threading

import pytest

from app.services import update_service as us


@pytest.fixture()
def release(tmp_path):
    setup = tmp_path / "Jon-Setup.exe"
    setup.write_bytes(b"MZ" + os.urandom(1_500_000))
    (tmp_path / "kaputt.exe").write_bytes(b"<html>404</html>" + b"x" * 1_500_000)
    (tmp_path / "kurz.exe").write_bytes(b"MZ" + b"\0" * 100)

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(tmp_path), **kw)

        def log_message(self, *a):
            pass

    server = socketserver.TCPServer(("127.0.0.1", 0), Quiet)
    port = server.server_address[1]
    base = f"http://127.0.0.1:{port}"
    (tmp_path / "latest.json").write_text(
        json.dumps(
            {
                "tag_name": "v9.9.9",
                "body": "Testrelease",
                "assets": [
                    {
                        "name": "Jon-Setup.exe",
                        "size": setup.stat().st_size,
                        "browser_download_url": f"{base}/Jon-Setup.exe",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield base, setup.stat().st_size
    server.shutdown()
    server.server_close()


@pytest.fixture()
def frozen(monkeypatch, tmp_path, release):
    base, _ = release
    monkeypatch.setattr(us, "UPDATE_DIR", tmp_path / "updates")
    monkeypatch.setattr(us, "ALLOWED_PREFIXES", ("https://", "http://127.0.0.1:"))
    monkeypatch.setattr(us, "RELEASES_API", f"{base}/latest.json")
    monkeypatch.setattr(us, "is_frozen", lambda: True)
    monkeypatch.setattr(us, "_cache", {"at": 0.0, "data": None})
    return us


_REAL_FETCH = us._fetch


def _published(version: str):
    def fake(url: str, timeout: float = 10.0) -> bytes:
        if url == us.RAW_CONFIG:
            return f'app_version: str = "{version}"'.encode()
        return _REAL_FETCH(url, timeout)

    return fake


def test_installationsart_wird_erkannt(monkeypatch):
    monkeypatch.setattr(us, "is_frozen", lambda: True)
    assert us.install_mode() == "exe"
    monkeypatch.setattr(us, "is_frozen", lambda: False)
    assert us.install_mode() in {"git", "manual"}


def test_exe_modus_bietet_das_fertige_release_an(frozen, release, monkeypatch):
    _, size = release
    monkeypatch.setattr(us, "_fetch", _published("9.9.9"))
    info = us.check_update(force=True)
    assert info["mode"] == "exe"
    assert info["latest"] == "9.9.9"
    assert info["installer_url"].endswith("Jon-Setup.exe")
    assert info["installer_size"] == size
    assert info["update"] is True
    assert info["can_install"] is True


def test_angekuendigte_version_ohne_installer_wird_nicht_installiert(frozen, monkeypatch):
    monkeypatch.setattr(us, "_release", lambda: {"version": "3.33.0"})
    monkeypatch.setattr(us, "_fetch", _published("99.0.0"))
    info = us.check_update(force=True)
    assert info["latest"] == "99.0.0"
    assert info["installer_url"] == ""
    assert info["can_install"] is False


def test_release_aelter_als_installiert_ist_kein_update(frozen, monkeypatch):
    monkeypatch.setattr(us, "_fetch", _published("1.0.0"))
    monkeypatch.setattr(
        us, "get_settings", lambda: type("S", (), {"app_version": "99.0.0"})()
    )
    info = us.check_update(force=True)
    assert info["latest"] == "9.9.9"
    assert info["update"] is False
    assert info["can_install"] is False


def test_download_nimmt_nur_ein_echtes_programm(frozen, release):
    base, size = release
    target = us.download_installer(f"{base}/Jon-Setup.exe", "9.9.9", size)
    assert target.name == "Jon-Setup-9.9.9.exe"
    assert target.read_bytes()[:2] == b"MZ"
    assert target.stat().st_size == size

    with pytest.raises(ValueError, match="kein Windows-Programm"):
        us.download_installer(f"{base}/kaputt.exe", "9.9.9")
    with pytest.raises(ValueError, match="unvollstaendig"):
        us.download_installer(f"{base}/kurz.exe", "9.9.9")
    with pytest.raises(ValueError, match="Groesse"):
        us.download_installer(f"{base}/Jon-Setup.exe", "9.9.9", size + 100_000)
    assert list(us.UPDATE_DIR.glob("*.part")) == []


def test_fremde_adresse_wird_abgelehnt(frozen, release):
    base, _ = release
    with pytest.raises(ValueError, match="Adresse"):
        us.download_installer(base.replace("http://", "ftp://") + "/Jon-Setup.exe", "9.9.9")
    with pytest.raises(ValueError, match="Adresse"):
        us.download_installer("http://beispiel.de/Jon-Setup.exe", "9.9.9")


def test_fortschritt_wird_gemeldet(frozen, release):
    base, size = release
    seen: list[tuple[int, int]] = []
    us.download_installer(f"{base}/Jon-Setup.exe", "9.9.9", size, lambda d, t: seen.append((d, t)))
    assert seen
    assert seen[-1] == (size, size)


def test_alte_installer_werden_aufgeraeumt(frozen, release):
    base, size = release
    us.UPDATE_DIR.mkdir(parents=True, exist_ok=True)
    alt = us.UPDATE_DIR / "Jon-Setup-1.0.0.exe"
    alt.write_bytes(b"MZalt")
    us.download_installer(f"{base}/Jon-Setup.exe", "9.9.9", size)
    assert not alt.exists()
    assert us.installer_path("9.9.9").exists()


def test_update_ablauf_meldet_den_installer(frozen, release, monkeypatch):
    monkeypatch.setattr(us, "_fetch", _published("9.9.9"))
    from app.services.update_process import perform_update

    async def run():
        return "".join([line async for line in perform_update()])

    text = asyncio.run(run())
    assert "Version 9.9.9 gefunden" in text
    assert "DONE" in text
    marker = [line for line in text.splitlines() if line.startswith("INSTALLER ")]
    assert marker, text
    assert marker[0].endswith("Jon-Setup-9.9.9.exe")
    assert us.installer_path("9.9.9").exists()


def test_aktuelle_version_laedt_nichts(frozen, monkeypatch):
    monkeypatch.setattr(us, "_release", lambda: {"version": "0.0.1"})
    monkeypatch.setattr(us, "_fetch", _published("0.0.1"))
    from app.services.update_process import perform_update

    async def run():
        return "".join([line async for line in perform_update()])

    text = asyncio.run(run())
    assert "ist aktuell" in text
    assert "INSTALLER" not in text
