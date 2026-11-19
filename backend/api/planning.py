"""
Router Calendrier d'entraînement : chaque sportif planifie ses séances.
Un utilisateur ne peut voir et modifier que SON planning (l'administrateur peut tout voir).
"""
import re
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database.db import get_connection
from api.deps import get_current_user

router = APIRouter(prefix="/api/planning", tags=["Calendrier d'entraînement"])


class PlanifCreate(BaseModel):
    exercice_id: int
    date_prevue: str            # AAAA-MM-JJ
    heure: str = "18:00"        # HH:MM
    note: Optional[str] = ""


class PlanifStatut(BaseModel):
    statut: str                 # 'prevue' | 'faite'


def _check(d: str, h: str):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) or not re.fullmatch(r"\d{2}:\d{2}", h):
        raise HTTPException(400, "Date (AAAA-MM-JJ) ou heure (HH:MM) invalide.")


@router.get("")
def list_planning(user=Depends(get_current_user)):
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.*, e.nom AS exercice_nom, e.groupe_musculaire
           FROM planifications p JOIN exercices e ON e.id = p.exercice_id
           WHERE p.sportif_id = ? ORDER BY p.date_prevue ASC, p.heure ASC""",
        (user.idUtilisateur,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("", status_code=201)
def create_planif(req: PlanifCreate, user=Depends(get_current_user)):
    _check(req.date_prevue, req.heure)
    conn = get_connection()
    if not conn.execute("SELECT id FROM exercices WHERE id = ?", (req.exercice_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Exercice introuvable.")
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO planifications (sportif_id, exercice_id, date_prevue, heure, note, statut)
           VALUES (?, ?, ?, ?, ?, 'prevue')""",
        (user.idUtilisateur, req.exercice_id, req.date_prevue, req.heure, (req.note or "")[:255]),
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"message": "Séance planifiée.", "id": new_id}


@router.put("/{planif_id}")
def update_statut(planif_id: int, req: PlanifStatut, user=Depends(get_current_user)):
    if req.statut not in ("prevue", "faite"):
        raise HTTPException(400, "Statut invalide.")
    conn = get_connection()
    cur = conn.execute("UPDATE planifications SET statut = ? WHERE id = ? AND sportif_id = ?",
                       (req.statut, planif_id, user.idUtilisateur))
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    if not ok:
        raise HTTPException(404, "Séance planifiée introuvable.")
    return {"message": "Statut mis à jour."}


@router.delete("/{planif_id}")
def delete_planif(planif_id: int, user=Depends(get_current_user)):
    conn = get_connection()
    cur = conn.execute("DELETE FROM planifications WHERE id = ? AND sportif_id = ?",
                       (planif_id, user.idUtilisateur))
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    if not ok:
        raise HTTPException(404, "Séance planifiée introuvable.")
    return {"message": "Séance supprimée du calendrier."}