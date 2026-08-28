from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

ROUTE_ENGINES = {
    "fuss": "fossgis_osrm_foot",
    "fahrrad": "fossgis_osrm_bike",
    "auto": "fossgis_osrm_car",
    "oepnv": "fossgis_osrm_car",
}

LEARN_COMMANDS = (
    "/lernen",
    "/lerne",
    "/deeplearning",
    "/lernstatus",
    "/lernstand",
    "/lernstop",
    "/lernstopp",
    "/lernweiter",
)


def _cards(cards: list[dict] | None, kind: str) -> list[dict]:
    return [
        dict(card.get("data") or {})
        for card in (cards or [])
        if isinstance(card, dict) and card.get("kind") == kind
    ]


def _point(place: Any, fallback: str = "Ort") -> dict | None:
    if not isinstance(place, dict):
        return None
    lat = place.get("lat")
    lon = place.get("lon")
    if lat is None or lon is None:
        return None
    return {
        "lat": float(lat),
        "lon": float(lon),
        "titel": str(place.get("name") or fallback),
        "label": str(place.get("label") or ""),
    }


def map_points(cards: list[dict] | None) -> list[dict]:
    punkte: list[dict] = []
    for data in _cards(cards, "maps"):
        aktion = str(data.get("aktion") or "")
        if aktion == "route":
            punkt = _point(data.get("ziel"), "Ziel")
        elif aktion == "erkunden":
            punkt = _point(data.get("ort"), "Ort")
        else:
            treffer = data.get("treffer") or []
            punkt = _point(treffer[0] if treffer else None)
            if punkt is None:
                mitte = data.get("mittelpunkt") or (data.get("karte") or {}).get(
                    "center"
                )
                punkt = _point(mitte, str(data.get("kategorie") or "In der Nähe"))
        if punkt is not None:
            punkte.append(punkt)
    return punkte


def map_links(cards: list[dict] | None) -> list[str]:
    links: list[str] = []
    for data in _cards(cards, "maps"):
        if str(data.get("aktion") or "") != "route":
            continue
        stationen = [
            station
            for station in (data.get("stationen") or [])
            if isinstance(station, dict) and station.get("lat") is not None
        ]
        if len(stationen) < 2:
            continue
        engine = ROUTE_ENGINES.get(
            str(data.get("modus") or "auto"), "fossgis_osrm_car"
        )
        route = "%3B".join(
            f"{float(station['lat']):.5f}%2C{float(station['lon']):.5f}"
            for station in stationen
        )
        links.append(
            f"https://www.openstreetmap.org/directions?engine={engine}&route={route}"
        )
    return links


def research_ids(cards: list[dict] | None) -> list[str]:
    ids: list[str] = []
    for data in _cards(cards, "deep_learning"):
        task_id = str(data.get("id") or "")
        if task_id and task_id not in ids:
            ids.append(task_id)
    return ids


def _percent(task: dict) -> int:
    return int(round(float(task.get("fortschritt") or 0.0) * 100))


def _line(task: dict) -> str:
    return (
        f"{task.get('titel') or task.get('thema') or 'Recherche'} · "
        f"{task.get('status')} · {_percent(task)}%"
    )


def research_report(task_id: str) -> str:
    from app.services.research import get_research_service

    service = get_research_service()
    try:
        task = service.get(task_id)
    except Exception:
        return ""
    status = str(task.get("status") or "")
    titel = str(task.get("titel") or task.get("thema") or "Recherche")
    kopf = {
        "fertig": "🎓 Deep Learning fertig",
        "abgebrochen": "🛑 Deep Learning abgebrochen",
        "fehler": "⚠️ Deep Learning gescheitert",
        "pausiert": "⏸️ Deep Learning pausiert",
    }.get(status, f"🎓 Deep Learning {status}")
    dateien = task.get("dateien") or []
    quellen = task.get("quellen") or []
    zeilen = [
        f"{kopf}: {titel}",
        f"{len(dateien)} Dateien · {len(quellen)} Quellen · {task.get('ordner', '')}",
    ]
    if task.get("fehler"):
        zeilen.append(f"Fehler: {task['fehler']}")
    text = str(task.get("zusammenfassung") or "").strip()
    if not text:
        try:
            text = service.read_file(task_id, "README").strip()
        except Exception:
            text = ""
    if text:
        zeilen.append("")
        zeilen.append(text[:2500])
    return "\n".join(zeilen)


async def watch_research(
    task_id: str, send: Callable[[str], Awaitable[None]]
) -> None:
    from app.services.research import get_research_service

    service = get_research_service()
    try:
        async for _ in service.stream(task_id):
            pass
    except asyncio.CancelledError:
        raise
    except Exception:
        pass
    bericht = research_report(task_id)
    if bericht:
        try:
            await send(bericht)
        except Exception:
            pass


def spawn_research_watch(
    task_id: str,
    send: Callable[[str], Awaitable[None]],
    running: dict[str, asyncio.Task],
) -> None:
    if not task_id or task_id in running:
        return
    try:
        task = asyncio.create_task(watch_research(task_id, send))
    except RuntimeError:
        return
    running[task_id] = task
    task.add_done_callback(lambda _: running.pop(task_id, None))


def is_learn_command(text: str) -> bool:
    raw = (text or "").strip()
    if not raw.startswith("/"):
        return False
    return raw.split()[0].split("@")[0].lower() in LEARN_COMMANDS


async def research_command(text: str) -> tuple[str, str] | None:
    raw = (text or "").strip()
    if not raw.startswith("/"):
        return None
    teile = raw.split(maxsplit=1)
    befehl = teile[0].split("@")[0].lower()
    rest = teile[1].strip() if len(teile) > 1 else ""
    if befehl not in LEARN_COMMANDS:
        return None
    from app.services.research import get_research_service

    service = get_research_service()
    if befehl in ("/lernen", "/lerne", "/deeplearning"):
        if not rest:
            return (
                "Sag mir, was ich lernen soll — zum Beispiel:\n"
                "/lernen Quantencomputer 30 Minuten",
                "",
            )
        try:
            task = await service.start(rest, 0)
        except Exception as exc:
            return (f"Das Lernen ging nicht los: {exc}", "")
        return (
            f"🎓 Ich lerne jetzt „{task.get('titel')}“ "
            f"({task.get('minuten')} Minuten). Ich melde mich, sobald ich fertig "
            "bin. /lernstatus zeigt den Stand, /lernstop bricht ab.",
            str(task.get("id") or ""),
        )
    if befehl in ("/lernstatus", "/lernstand"):
        aktiv = service.active()
        if aktiv:
            zeilen = "\n".join(f"• {service.status_text(t)}" for t in aktiv)
            return (f"🎓 Ich lerne gerade:\n{zeilen}", "")
        letzte = service.list()[:3]
        if not letzte:
            return ("Ich lerne gerade nichts. Starte mit /lernen <Thema>.", "")
        zeilen = "\n".join(f"• {_line(task)}" for task in letzte)
        return (f"Gerade lerne ich nichts. Zuletzt:\n{zeilen}", "")
    if befehl in ("/lernstop", "/lernstopp"):
        aktiv = service.active()
        ziel = rest or (str(aktiv[0]["id"]) if aktiv else "")
        if not ziel:
            return ("Es läuft gerade keine Recherche. 👍", "")
        try:
            task = service.stop(ziel)
        except Exception as exc:
            return (f"Das ging nicht: {exc}", "")
        return (
            f"🛑 Abgebrochen: {task.get('titel')}. Der Fortschritt ist gesichert, "
            "mit /lernweiter mache ich weiter.",
            "",
        )
    aktiv = service.active()
    if aktiv:
        return (f"Läuft doch schon: {service.status_text(aktiv[0])}", "")
    offen = [
        task
        for task in service.list()
        if task.get("status") in ("pausiert", "abgebrochen", "unterbrochen", "fehler")
    ]
    ziel = rest or (str(offen[0]["id"]) if offen else "")
    if not ziel:
        return ("Da ist nichts zum Fortsetzen. Starte mit /lernen <Thema>.", "")
    try:
        task = await service.resume_task(ziel)
    except Exception as exc:
        return (f"Das ging nicht: {exc}", "")
    return (
        f"▶️ Ich lerne weiter an „{task.get('titel')}“.",
        str(task.get("id") or ""),
    )
