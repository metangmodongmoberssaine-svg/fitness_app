"""
Router Vision & Traitement d'images.
Fournit :
- La liste des vidéos d'entraînement échantillons disponibles en local.
- L'évaluation d'une trame ou d'une posture via les classes métier Python (MoteurVision, CompteurRepetitions).
"""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from domain.point_cle import PointCle
from domain.posture import Posture
from domain.regle_de_comptage import RegleDeComptage
from domain.compteur_repetitions import CompteurRepetitions

router = APIRouter(prefix="/api/vision", tags=["Vision par ordinateur"])

SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "samples")


class PointPayload(BaseModel):
    nom: str
    x: float
    y: float
    z: float = 0.0
    visibilite: float = 1.0


class EvaluatePostureRequest(BaseModel):
    exercice_id: int
    points: List[PointPayload]
    regle: Optional[Dict[str, Any]] = None


@router.get("/samples")
def get_sample_videos():
    """Retourne la liste des vidéos locales disponibles pour test."""
    if not os.path.exists(SAMPLES_DIR):
        return []
    videos = []
    for f in os.listdir(SAMPLES_DIR):
        if f.lower().endswith((".mp4", ".avi", ".mov", ".webm")):
            videos.append({
                "filename": f,
                "url": f"/samples/{f}",
                "size_bytes": os.path.getsize(os.path.join(SAMPLES_DIR, f))
            })
    return sorted(videos, key=lambda x: x["filename"])


@router.post("/evaluer-posture")
def evaluer_posture(req: EvaluatePostureRequest):
    """
    Exécute le calcul de posture via le modèle objet Python (Posture -> PointCle -> getAngle).
    Permet de vérifier le comportement de calcul d'angle et de tolérance côté serveur.
    """
    if len(req.points) < 15:
        return {"valide": False, "message": "Trop peu de points pour estimer la posture"}

    points_cles = [PointCle(p.nom, p.x, p.y, p.z, p.visibilite) for p in req.points]
    posture = Posture(pointsCles=points_cles)

    regle_data = req.regle or {
        "articulation_cle": "genou",
        "angle_haut": 160.0,
        "angle_bas": 90.0,
        "tolerance": 10.0,
        "duree_min_repetition": 600
    }

    regle = RegleDeComptage(
        articulationCle=regle_data.get("articulation_cle", "genou"),
        angleHaut=float(regle_data.get("angle_haut", 160.0)),
        angleBas=float(regle_data.get("angle_bas", 90.0)),
        tolerance=float(regle_data.get("tolerance", 10.0)),
        dureeMinRepetition=int(regle_data.get("duree_min_repetition", 600))
    )

    compteur = CompteurRepetitions(regle)
    rep_validee, correction, nouvelle_rep, angle = compteur.traiter(posture)

    return {
        "angle": round(angle, 1),
        "phase": compteur.phaseCourante,
        "repetition_validee": rep_validee,
        "correction": correction.to_dict() if correction else None,
        "repetition": nouvelle_rep.to_dict() if nouvelle_rep else None
    }
