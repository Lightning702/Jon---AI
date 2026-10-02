from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.fitness_service import FitnessFehler, get_fitness_service

router = APIRouter(prefix="/api/fitness")


@router.get("")
def overview(tage: int = 7) -> dict:
    return get_fitness_service().uebersicht(tage)


@router.post("/training")
def add_workout(payload: dict) -> dict:
    try:
        return get_fitness_service().training_eintragen(payload)
    except FitnessFehler as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/training/{training_id}")
def delete_workout(training_id: str) -> dict:
    return {"geloescht": get_fitness_service().training_loeschen(training_id)}


@router.post("/schritte")
def report_steps(payload: dict) -> dict:
    try:
        return get_fitness_service().schritte_melden(payload.get("tage") or {}, str(payload.get("quelle") or "handy"))
    except FitnessFehler as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/sync")
def sync(payload: dict) -> dict:
    return get_fitness_service().abgleichen(
        payload.get("trainings"), payload.get("geloescht"), payload.get("schritte"), str(payload.get("quelle") or "handy")
    )


@router.put("/ziele")
def set_goals(payload: dict) -> dict:
    try:
        return get_fitness_service().ziel_setzen(payload.get("schritte"), payload.get("trainings_pro_woche"))
    except FitnessFehler as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/gewicht")
def add_weight(payload: dict) -> dict:
    try:
        return get_fitness_service().gewicht_eintragen(payload.get("kg"), payload.get("datum"))
    except FitnessFehler as exc:
        raise HTTPException(status_code=400, detail=str(exc))
