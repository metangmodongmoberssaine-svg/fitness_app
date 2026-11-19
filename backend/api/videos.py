"""
Router Vidéos d'exercices.
- Tout le monde peut LIRE les vidéos (catalogue, démonstration avant séance).
- Seul l'ADMINISTRATEUR peut en ajouter ou en supprimer.
Les fichiers sont stockés sur disque (backend/uploads/videos) ; MySQL ne garde que le chemin
et qui l'a ajoutée (table videos_exercices).
"""
import os
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from database.db import get_connection
from api.deps import require_admin

router = APIRouter(prefix="/api/videos", tags=["Vidéos d'exercices"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "videos")
ALLOWED_EXT = {".mp4", ".webm", ".mov"}
MAX_BYTES = 100 * 1024 * 1024  # 100 Mo
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _row_to_dict(r) -> dict:
    d = dict(r)
    d["url"] = "/uploads/videos/" + os.path.basename(d["chemin"])
    d["ajoute_par"] = f"{d.pop('prenom', '') or ''} {d.pop('nom', '') or ''}".strip() or "—"
    return d


@router.get("")
def list_videos(exercice_id: Optional[int] = None):
    conn = get_connection()
    q = """SELECT v.*, u.prenom, u.nom FROM videos_exercices v
           LEFT JOIN utilisateurs u ON u.id = v.uploaded_by"""
    params = ()
    if exercice_id:
        q += " WHERE v.exercice_id = ?"
        params = (exercice_id,)
    q += " ORDER BY v.id DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


@router.post("", status_code=201)
async def upload_video(
    exercice_id: int = Form(...),
    titre: str = Form(""),
    fichier: UploadFile = File(...),
    admin=Depends(require_admin),
):
    ext = os.path.splitext(fichier.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "Format non accepté. Utilisez .mp4, .webm ou .mov.")

    conn = get_connection()
    if not conn.execute("SELECT id FROM exercices WHERE id = ?", (exercice_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Exercice introuvable.")

    nom_fichier = f"{uuid.uuid4().hex}{ext}"
    chemin = os.path.join(UPLOAD_DIR, nom_fichier)
    taille = 0
    try:
        with open(chemin, "wb") as out:
            while True:
                bloc = await fichier.read(1024 * 1024)
                if not bloc:
                    break
                taille += len(bloc)
                if taille > MAX_BYTES:
                    raise HTTPException(413, "Vidéo trop lourde (100 Mo maximum).")
                out.write(bloc)
    except HTTPException:
        out.close()
        os.remove(chemin)
        conn.close()
        raise

    cur = conn.cursor()
    cur.execute(
        """INSERT INTO videos_exercices (exercice_id, titre, chemin, taille_octets, uploaded_by, date_ajout)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (exercice_id, (titre or fichier.filename or "")[:150], nom_fichier, taille,
         admin.idUtilisateur, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"message": "Vidéo ajoutée.", "id": new_id, "url": f"/uploads/videos/{nom_fichier}"}


@router.delete("/{video_id}")
def delete_video(video_id: int, admin=Depends(require_admin)):
    conn = get_connection()
    row = conn.execute("SELECT chemin FROM videos_exercices WHERE id = ?", (video_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Vidéo introuvable.")
    conn.execute("DELETE FROM videos_exercices WHERE id = ?", (video_id,))
    conn.commit()
    conn.close()
    try:
        os.remove(os.path.join(UPLOAD_DIR, os.path.basename(row["chemin"])))
    except OSError:
        pass
    return {"message": "Vidéo supprimée."}