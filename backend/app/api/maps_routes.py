from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import MapsActionIn, MapsHomeIn, MapsRouteIn, MapsSharingIn
from app.services.friend_location_service import get_friend_location_service
from app.services.maps import MapsError, get_maps_service
from app.services.p2p_service import get_p2p_service

router = APIRouter(prefix="/api/maps")


@router.get("/config")
async def maps_config() -> dict:
    service = get_maps_service()
    data = service.config()
    data["standort"] = await service.home_details()
    return data


@router.get("/home")
async def maps_home() -> dict:
    return await get_maps_service().home_details()


@router.post("/home")
async def maps_set_home(payload: MapsHomeIn) -> dict:
    try:
        return await get_maps_service().set_home(
            payload.lat, payload.lon, payload.source
        )
    except MapsError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/locate")
async def maps_locate(force: bool = True) -> dict:
    service = get_maps_service()
    fix = await service.locate_device(force)
    if fix is None:
        raise HTTPException(
            status_code=404,
            detail="Windows hat keinen Standort geliefert. Prüfe unter "
            "Einstellungen → Datenschutz → Standort, ob der Standortdienst an ist.",
        )
    saved = await service.set_home(fix["lat"], fix["lon"], "geraet")
    saved["genauigkeit_m"] = fix.get("genauigkeit_m")
    return saved


@router.get("/friends")
async def maps_friends() -> dict:
    service = get_friend_location_service()
    peers = get_p2p_service().peers()
    return {
        "freunde": service.friends(peers),
        "teilen": service.sharing(),
        "zuletzt_gesendet": service.last_sent(),
        "kontakte": [
            {"id": peer["id"], "name": peer["name"], "avatar": peer["avatar"]}
            for peer in peers
        ],
    }


@router.put("/friends/sharing")
async def maps_set_sharing(payload: MapsSharingIn) -> dict:
    service = get_friend_location_service()
    state = service.set_sharing(payload.aktiv, payload.alle, payload.peers)
    if state.get("aktiv"):
        await service.broadcast(force=True)
    return state


@router.post("/friends/ping")
async def maps_share_now() -> dict:
    return await get_friend_location_service().broadcast(force=True)


@router.delete("/friends")
async def maps_clear_friends() -> dict:
    return {"geloescht": get_friend_location_service().clear()}


@router.get("/styles/{theme}")
async def maps_style(theme: str) -> dict:
    return await get_maps_service().style(theme)


@router.get("/search")
async def maps_search(
    q: str,
    lat: float | None = None,
    lon: float | None = None,
    limit: int = 8,
) -> dict:
    service = get_maps_service()
    near = (lat, lon) if lat is not None and lon is not None else None
    try:
        places = await service.search(q, near, limit)
    except MapsError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Suche nicht möglich: {exc}")
    return {"treffer": [place.to_dict() for place in places]}


@router.get("/nearby")
async def maps_nearby(
    category: str,
    lat: float,
    lon: float,
    radius: int = 1500,
    limit: int = 20,
) -> dict:
    try:
        places = await get_maps_service().places(category, lat, lon, radius, limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Umgebung nicht ladbar: {exc}")
    return {"treffer": [place.to_dict() for place in places]}


@router.get("/reverse")
async def maps_reverse(lat: float, lon: float) -> dict:
    try:
        place = await get_maps_service().reverse(lat, lon)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ort nicht ladbar: {exc}")
    if place is None:
        raise HTTPException(status_code=404, detail="Kein Ort an dieser Stelle")
    return place.to_dict()


@router.post("/route")
async def maps_route(payload: MapsRouteIn) -> dict:
    service = get_maps_service()
    try:
        points = [(point.lat, point.lon) for point in payload.points]
        options = await service.route(points, payload.mode, payload.alternatives)
    except MapsError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Routing nicht möglich: {exc}")
    return {"routen": [option.to_dict() for option in options]}


@router.get("/street")
async def maps_street(
    lat: float, lon: float, radius: int = 150, limit: int = 24
) -> dict:
    return await get_maps_service().street_images(lat, lon, radius, limit)


@router.get("/street/sequence/{sequence_id}")
async def maps_street_sequence(sequence_id: str, limit: int = 60) -> dict:
    return {"bilder": await get_maps_service().street_sequence(sequence_id, limit)}


@router.post("/action")
async def maps_action(payload: MapsActionIn) -> dict:
    try:
        return await get_maps_service().answer(payload.action, payload.args)
    except MapsError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
