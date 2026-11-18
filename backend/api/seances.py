"""
Router Séances d'Entraînement.
Diagrammes de Séquence (Figures 4, 5, 6) & Diagramme d'Activité (Figure 7).
Phase 1 : POST /api/seances -> INSERT séance -> 201 Created + idSeance.
Phase 3 : PUT /api/seances/{id} -> UPDATE + INSERT répétitions + verifierAtteinte(total) + émission notification.
"""
from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from database.repository import SeanceRepository

router = APIRouter(prefix="/api/seances", tags=["Séances"])


class SeanceStartRequest(BaseModel):
    sportif_id: int
    exercice_id: int
    objectif_id: Optional[int] = None


class RepetitionPayload(BaseModel):
    numero: int
    horodatage: float
    duree_ms: int
    amplitude: float
    est_correcte: bool = True


class CorrectionPayload(BaseModel):
    message: str
    type: str = "mixte"
    gravite: int = 1
    horodatage: Optional[float] = None


class SeanceClotureRequest(BaseModel):
    duree_secondes: int
    total_repetitions: int
    repetitions: Optional[List[RepetitionPayload]] = []
    retours_correction: Optional[List[CorrectionPayload]] = []


@router.post("", status_code=status.HTTP_201_CREATED)
def demarrer_seance(req: SeanceStartRequest):
    """
    Spécifié dans le Diagramme de Séquence (Figure 4 - Messages 14 à 17) :
    Application -> POST /seances -> INSERT séance -> 201 Created + idSeance.
    """
    id_seance = SeanceRepository.create(
        sportif_id=req.sportif_id,
        exercice_id=req.exercice_id,
        objectif_id=req.objectif_id
    )
    return {
        "idSeance": id_seance,
        "id": id_seance,
        "message": "Séance initialisée avec succès"
    }


@router.put("/{seance_id}", status_code=status.HTTP_200_OK)
def cloturer_seance(seance_id: int, req: SeanceClotureRequest):
    """
    Spécifié dans le Diagramme de Séquence (Figure 6 - Messages 9 à 15) :
    Application -> PUT /seances/{id} (total, durée, répétitions) ->
    Serveur API -> UPDATE séance + INSERT répétitions -> verifierAtteinte(total) ->
    [objectif atteint] notification -> 200 OK + récapitulatif.
    """
    try:
        reps_data = [r.dict() for r in req.repetitions] if req.repetitions else []
        corrs_data = [c.dict() for c in req.retours_correction] if req.retours_correction else []

        result = SeanceRepository.cloturer(
            seance_id=seance_id,
            duree_secondes=req.duree_secondes,
            total_repetitions=req.total_repetitions,
            repetitions=reps_data,
            corrections=corrs_data
        )
        return {
            "message": "Séance clôturée et enregistrée avec succès",
            "recapitulatif": result["seance"],
            "objectif_atteint": result["objectif_atteint"],
            "notification": result["notification"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/historique")
def get_historique(sportif_id: int = Query(...)):
    """Consulter l'historique des séances d'un sportif."""
    return SeanceRepository.get_historique_by_sportif(sportif_id)


@router.get("/{seance_id}")
def get_seance(seance_id: int):
    """Afficher le récapitulatif détaillé d'une séance (Figure 6 - Message 15)."""
    seance = SeanceRepository.get_by_id(seance_id)
    if not seance:
        raise HTTPException(status_code=404, detail="Séance non trouvée.")
    return seance
