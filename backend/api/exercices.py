"""
Router Exercices & Catalogue.
Cas d'utilisation : Consulter le catalogue d'exercices (Visiteur/Sportif/Admin),
Gérer le catalogue d'exercices (Admin), Paramétrer les règles de comptage (Admin).
Diagramme de séquence Figure 4 : GET /exercices/{id} -> renvoie exercice + règle de comptage.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
from database.repository import ExerciceRepository

router = APIRouter(prefix="/api/exercices", tags=["Exercices & Catalogue"])


class RegleCreate(BaseModel):
    articulation_cle: str
    angle_haut: float
    angle_bas: float
    tolerance: float = 10.0
    duree_min_repetition: int = 600


class ExerciceCreateRequest(BaseModel):
    nom: str
    description: str
    groupe_musculaire: str
    difficulte: int = 1
    video_sample: Optional[str] = ""
    regle: RegleCreate


class ExerciceUpdateRequest(BaseModel):
    nom: str
    description: str
    groupe_musculaire: str
    difficulte: int
    video_sample: Optional[str] = ""
    regle: RegleCreate


@router.get("")
def list_exercices(groupe: Optional[str] = None, difficulte: Optional[int] = None):
    """Consulter le catalogue d'exercices."""
    all_exos = ExerciceRepository.get_all()
    if groupe:
        all_exos = [e for e in all_exos if groupe.lower() in e["groupe_musculaire"].lower()]
    if difficulte:
        all_exos = [e for e in all_exos if e["difficulte"] == difficulte]
    return all_exos


@router.get("/{exercice_id}")
def get_exercice(exercice_id: int):
    """
    Spécifié dans le Diagramme de Séquence (Figure 4 - Phase 1) :
    Application -> GET /exercices/{id} -> Serveur API -> SELECT -> renvoie exercice + règle de comptage.
    """
    exo = ExerciceRepository.get_by_id(exercice_id)
    if not exo:
        raise HTTPException(status_code=404, detail="Exercice introuvable.")
    return exo


@router.post("", status_code=201)
def create_exercice(req: ExerciceCreateRequest):
    """Gérer le catalogue + Paramétrer les règles de comptage (Admin)."""
    nouveau = ExerciceRepository.create(
        nom=req.nom,
        description=req.description,
        groupe_musculaire=req.groupe_musculaire,
        difficulte=req.difficulte,
        video_sample=req.video_sample or "",
        regle=req.regle.dict()
    )
    return {
        "message": "Exercice et règle de comptage créés avec succès",
        "exercice": nouveau
    }


@router.put("/{exercice_id}")
def update_exercice(exercice_id: int, req: ExerciceUpdateRequest):
    """Paramétrer les règles de comptage et mettre à jour le catalogue (Admin)."""
    existant = ExerciceRepository.get_by_id(exercice_id)
    if not existant:
        raise HTTPException(status_code=404, detail="Exercice introuvable.")
    
    maj = ExerciceRepository.update(
        exercice_id=exercice_id,
        nom=req.nom,
        description=req.description,
        groupe_musculaire=req.groupe_musculaire,
        difficulte=req.difficulte,
        video_sample=req.video_sample or "",
        regle=req.regle.dict()
    )
    return {
        "message": "Exercice et règle de comptage mis à jour avec succès",
        "exercice": maj
    }


@router.delete("/{exercice_id}")
def delete_exercice(exercice_id: int):
    """Suppression d'un exercice et de sa règle (en cascade)."""
    existant = ExerciceRepository.get_by_id(exercice_id)
    if not existant:
        raise HTTPException(status_code=404, detail="Exercice introuvable.")
    ExerciceRepository.delete(exercice_id)
    return {"message": "Exercice supprimé avec succès"}
