"""
Router Objectifs & Progression.
Cas d'utilisation : Définir un objectif (Sportif), Consulter la progression (Sportif).
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from database.repository import ObjectifRepository

router = APIRouter(prefix="/api/objectifs", tags=["Objectifs & Progression"])


class ObjectifCreateRequest(BaseModel):
    sportif_id: int
    exercice_id: int
    repetitions_cible: int
    periode: str = "quotidien"
    date_limite: Optional[str] = ""


@router.get("")
def list_objectifs(sportif_id: int = Query(...)):
    """Consulter la progression et la liste des objectifs d'un sportif."""
    return ObjectifRepository.get_by_sportif(sportif_id)


@router.post("", status_code=201)
def create_objectif(req: ObjectifCreateRequest):
    """Définir un objectif personnel pour un exercice donné."""
    res = ObjectifRepository.create(
        sportif_id=req.sportif_id,
        exercice_id=req.exercice_id,
        repetitions_cible=req.repetitions_cible,
        periode=req.periode,
        date_limite=req.date_limite or ""
    )
    return res
