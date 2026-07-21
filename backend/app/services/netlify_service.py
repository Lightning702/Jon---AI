from __future__ import annotations

import asyncio
import io
import subprocess
import time
import zipfile
from pathlib import Path

import httpx

from app.services.settings_service import get_settings_service

API = "https://api.netlify.com/api/v1"
ROOT = Path(__file__).resolve().parents[3]
WEBSITE = ROOT / "website"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _jon_zip_bauen() -> int:
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True, capture_output=True)
    zeilen = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.splitlines()
    dateien = [f for f in zeilen if f and f != "MEMORY.md" and f != "website/jon.zip"]
    with zipfile.ZipFile(WEBSITE / "jon.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo("Jon/"), "")
        for f in sorted(dateien):
            daten = (ROOT / f).read_bytes()
            info = zipfile.ZipInfo("Jon/" + f)
            if f.endswith(".sh"):
                daten = daten.replace(b"\r\n", b"\n")
                info.external_attr = 0o755 << 16
            z.writestr(info, daten, zipfile.ZIP_DEFLATED)
    return len(dateien)


def _website_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for pfad in sorted(WEBSITE.rglob("*")):
            if pfad.is_file():
                z.write(pfad, pfad.relative_to(WEBSITE).as_posix())
    return buf.getvalue()


class NetlifyService:
    def status(self) -> dict:
        s = get_settings_service().get()
        return {
            "token_set": bool(s.get("netlify_token")),
            "site_id": s.get("netlify_site_id", ""),
            "site_name": s.get("netlify_site_name", ""),
            "site_url": s.get("netlify_site_url", ""),
            "website_found": WEBSITE.is_dir(),
        }

    async def set_token(self, token: str) -> dict:
        token = (token or "").strip()
        if not token:
            get_settings_service().update(
                {
                    "netlify_token": "",
                    "netlify_site_id": "",
                    "netlify_site_name": "",
                    "netlify_site_url": "",
                }
            )
            return {"token_set": False}
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(f"{API}/user", headers=_auth(token))
        if res.status_code != 200:
            raise ValueError(
                "Netlify hat den Token abgelehnt. Erstelle unter "
                "app.netlify.com/user/applications einen Personal Access Token."
            )
        daten = res.json()
        get_settings_service().update({"netlify_token": token})
        return {
            "token_set": True,
            "email": daten.get("email", ""),
            "name": daten.get("full_name", ""),
        }

    async def sites(self) -> list[dict]:
        s = get_settings_service().get()
        token = s.get("netlify_token", "")
        if not token:
            raise ValueError("Kein Netlify-Token hinterlegt.")
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(f"{API}/sites?per_page=100", headers=_auth(token))
        if res.status_code != 200:
            raise ValueError(f"Netlify-Fehler {res.status_code} beim Laden der Websites.")
        return [
            {
                "id": site.get("id", ""),
                "name": site.get("name", ""),
                "url": site.get("ssl_url") or site.get("url", ""),
            }
            for site in res.json()
        ]

    def set_site(self, site_id: str, name: str, url: str) -> dict:
        if not site_id.strip():
            raise ValueError("Keine Website ausgewaehlt.")
        get_settings_service().update(
            {
                "netlify_site_id": site_id.strip(),
                "netlify_site_name": name.strip(),
                "netlify_site_url": url.strip(),
            }
        )
        return self.status()

    async def deploy(self) -> dict:
        s = get_settings_service().get()
        token = s.get("netlify_token", "")
        site_id = s.get("netlify_site_id", "")
        if not token:
            raise ValueError("Kein Netlify-Token hinterlegt.")
        if not site_id:
            raise ValueError("Keine Website ausgewaehlt.")
        if not WEBSITE.is_dir():
            raise ValueError("website-Ordner nicht gefunden.")
        start = time.monotonic()
        jon_zip_dateien = 0
        try:
            jon_zip_dateien = await asyncio.to_thread(_jon_zip_bauen)
        except Exception:
            pass
        daten = await asyncio.to_thread(_website_zip)
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                f"{API}/sites/{site_id}/deploys",
                headers={**_auth(token), "Content-Type": "application/zip"},
                content=daten,
            )
            if res.status_code not in (200, 201):
                raise ValueError(
                    f"Netlify-Fehler {res.status_code}: {res.text[:200]}"
                )
            info = res.json()
            deploy_id = info.get("id", "")
            zustand = info.get("state", "")
            for _ in range(45):
                if zustand in ("ready", "error"):
                    break
                await asyncio.sleep(2)
                poll = await client.get(
                    f"{API}/deploys/{deploy_id}", headers=_auth(token)
                )
                if poll.status_code == 200:
                    info = poll.json()
                    zustand = info.get("state", zustand)
        if zustand == "error":
            raise ValueError("Netlify meldet einen Fehler beim Verarbeiten des Deploys.")
        return {
            "state": zustand,
            "url": info.get("ssl_url") or info.get("url") or s.get("netlify_site_url", ""),
            "deploy_url": info.get("deploy_ssl_url", ""),
            "dauer": round(time.monotonic() - start, 1),
            "zip_kb": len(daten) // 1024,
            "jon_zip_dateien": jon_zip_dateien,
        }


_service: NetlifyService | None = None


def get_netlify_service() -> NetlifyService:
    global _service
    if _service is None:
        _service = NetlifyService()
    return _service
