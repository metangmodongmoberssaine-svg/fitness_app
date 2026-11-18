"""
Couche Repository - Fait le pont entre les tables SQLite et les classes du domaine métier.
Implémente la logique d'enregistrement, d'historique, de calcul d'objectifs et de statistiques.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from database.db import get_connection, hash_password
from domain.utilisateur import Sportif, Administrateur, Utilisateur
from domain.exercice import Exercice
from domain.regle_de_comptage import RegleDeComptage
from domain.seance_entrainement import SeanceEntrainement
from domain.repetition import Repetition
from domain.retour_correction import RetourCorrection
from domain.objectif import Objectif
from domain.notification import Notification


class AuthRepository:
    @staticmethod
    def get_by_email(email: str) -> Optional[Utilisateur]:
        conn = get_connection()
        row = conn.execute("SELECT * FROM utilisateurs WHERE email = ?", (email.lower().strip(),)).fetchone()
        conn.close()
        if not row:
            return None
        return AuthRepository._row_to_user(row)

    @staticmethod
    def get_by_id(user_id: int) -> Optional[Utilisateur]:
        conn = get_connection()
        row = conn.execute("SELECT * FROM utilisateurs WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        if not row:
            return None
        return AuthRepository._row_to_user(row)

    @staticmethod
    def create_user(nom: str, prenom: str, email: str, mot_de_passe_clair: str, role: str = "sportif",
                    poids: float = 70.0, taille: float = 175.0, niveau: str = "Intermédiaire") -> Utilisateur:
        conn = get_connection()
        mdp_hash = hash_password(mot_de_passe_clair)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO utilisateurs (nom, prenom, email, mot_de_passe_hash, date_inscription, role, poids, taille, niveau, niveau_acces)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (nom, prenom, email.lower().strip(), mdp_hash, datetime.now().isoformat(), role, poids, taille, niveau, 2 if role == "administrateur" else 1))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return AuthRepository.get_by_id(user_id)

    @staticmethod
    def update_profile(user_id: int, nom: str, prenom: str, email: str, poids: float, taille: float, niveau: str) -> bool:
        conn = get_connection()
        conn.execute("""
        UPDATE utilisateurs 
        SET nom = ?, prenom = ?, email = ?, poids = ?, taille = ?, niveau = ?
        WHERE id = ?
        """, (nom, prenom, email.lower().strip(), poids, taille, niveau, user_id))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def _row_to_user(row) -> Utilisateur:
        if row["role"] == "administrateur":
            return Administrateur(
                idUtilisateur=row["id"],
                nom=row["nom"],
                prenom=row["prenom"],
                email=row["email"],
                motDePasse=row["mot_de_passe_hash"],
                niveauAcces=row["niveau_acces"],
                dateInscription=row["date_inscription"]
            )
        else:
            return Sportif(
                idUtilisateur=row["id"],
                nom=row["nom"],
                prenom=row["prenom"],
                email=row["email"],
                motDePasse=row["mot_de_passe_hash"],
                poids=row["poids"],
                taille=row["taille"],
                niveau=row["niveau"],
                dateInscription=row["date_inscription"]
            )


class ExerciceRepository:
    @staticmethod
    def get_all() -> List[dict]:
        conn = get_connection()
        rows = conn.execute("""
        SELECT e.*, 
               r.id as regle_id, r.articulation_cle, r.angle_haut, r.angle_bas, r.tolerance, r.duree_min_repetition
        FROM exercices e
        LEFT JOIN regles_comptage r ON e.id = r.exercice_id
        ORDER BY e.id ASC
        """).fetchall()
        conn.close()

        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "nom": r["nom"],
                "description": r["description"],
                "groupe_musculaire": r["groupe_musculaire"],
                "difficulte": r["difficulte"],
                "video_sample": r["video_sample"],
                "regle": {
                    "id": r["regle_id"],
                    "exercice_id": r["id"],
                    "articulation_cle": r["articulation_cle"],
                    "angle_haut": r["angle_haut"],
                    "angle_bas": r["angle_bas"],
                    "tolerance": r["tolerance"],
                    "duree_min_repetition": r["duree_min_repetition"]
                } if r["regle_id"] else None
            })
        return result

    @staticmethod
    def get_by_id(exercice_id: int) -> Optional[dict]:
        conn = get_connection()
        row = conn.execute("""
        SELECT e.*, 
               r.id as regle_id, r.articulation_cle, r.angle_haut, r.angle_bas, r.tolerance, r.duree_min_repetition
        FROM exercices e
        LEFT JOIN regles_comptage r ON e.id = r.exercice_id
        WHERE e.id = ?
        """, (exercice_id,)).fetchone()
        conn.close()
        if not row:
            return None
        return {
            "id": row["id"],
            "nom": row["nom"],
            "description": row["description"],
            "groupe_musculaire": row["groupe_musculaire"],
            "difficulte": row["difficulte"],
            "video_sample": row["video_sample"],
            "regle": {
                "id": row["regle_id"],
                "exercice_id": row["id"],
                "articulation_cle": row["articulation_cle"],
                "angle_haut": row["angle_haut"],
                "angle_bas": row["angle_bas"],
                "tolerance": row["tolerance"],
                "duree_min_repetition": row["duree_min_repetition"]
            } if row["regle_id"] else None
        }

    @staticmethod
    def create(nom: str, description: str, groupe_musculaire: str, difficulte: int, regle: dict, video_sample: str = "") -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO exercices (nom, description, groupe_musculaire, difficulte, video_sample)
        VALUES (?, ?, ?, ?, ?)
        """, (nom, description, groupe_musculaire, difficulte, video_sample))
        exo_id = cursor.lastrowid

        cursor.execute("""
        INSERT INTO regles_comptage (exercice_id, articulation_cle, angle_haut, angle_bas, tolerance, duree_min_repetition)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            exo_id,
            regle.get("articulation_cle", "genou"),
            float(regle.get("angle_haut", 160.0)),
            float(regle.get("angle_bas", 90.0)),
            float(regle.get("tolerance", 10.0)),
            int(regle.get("duree_min_repetition", 600))
        ))
        conn.commit()
        conn.close()
        return ExerciceRepository.get_by_id(exo_id)

    @staticmethod
    def update(exercice_id: int, nom: str, description: str, groupe_musculaire: str, difficulte: int, regle: dict, video_sample: str = "") -> Optional[dict]:
        conn = get_connection()
        conn.execute("""
        UPDATE exercices
        SET nom = ?, description = ?, groupe_musculaire = ?, difficulte = ?, video_sample = ?
        WHERE id = ?
        """, (nom, description, groupe_musculaire, difficulte, video_sample, exercice_id))

        if regle:
            cur = conn.execute("""
            UPDATE regles_comptage
            SET articulation_cle = ?, angle_haut = ?, angle_bas = ?, tolerance = ?, duree_min_repetition = ?
            WHERE exercice_id = ?
            """, (
                regle.get("articulation_cle", "genou"),
                float(regle.get("angle_haut", 160.0)),
                float(regle.get("angle_bas", 90.0)),
                float(regle.get("tolerance", 10.0)),
                int(regle.get("duree_min_repetition", 600)),
                exercice_id
            ))
            if cur.rowcount == 0:
                conn.execute("""
                INSERT INTO regles_comptage (exercice_id, articulation_cle, angle_haut, angle_bas, tolerance, duree_min_repetition)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    exercice_id,
                    regle.get("articulation_cle", "genou"),
                    float(regle.get("angle_haut", 160.0)),
                    float(regle.get("angle_bas", 90.0)),
                    float(regle.get("tolerance", 10.0)),
                    int(regle.get("duree_min_repetition", 600))
                ))
        conn.commit()
        conn.close()
        return ExerciceRepository.get_by_id(exercice_id)

    @staticmethod
    def delete(exercice_id: int) -> bool:
        conn = get_connection()
        conn.execute("DELETE FROM exercices WHERE id = ?", (exercice_id,))
        conn.commit()
        conn.close()
        return True


class SeanceRepository:
    @staticmethod
    def create(sportif_id: int, exercice_id: int, objectif_id: Optional[int] = None) -> int:
        """Phase 1 du diagramme de séquence : POST /seances -> INSERT séance -> 201 Created + idSeance."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO seances_entrainement (sportif_id, exercice_id, objectif_id, date_debut, duree_secondes, statut, total_repetitions)
        VALUES (?, ?, ?, ?, 0, 'en_cours', 0)
        """, (sportif_id, exercice_id, objectif_id, datetime.now().isoformat()))
        seance_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return seance_id

    @staticmethod
    def cloturer(seance_id: int, duree_secondes: int, total_repetitions: int,
                 repetitions: List[dict] = None, corrections: List[dict] = None) -> Dict[str, Any]:
        """
        Phase 3 du diagramme de séquence :
        PUT /seances/{id} -> UPDATE séance + INSERT répétitions + verifierAtteinte(total).
        """
        conn = get_connection()
        cursor = conn.cursor()

        # 1. Update séance
        cursor.execute("""
        UPDATE seances_entrainement
        SET duree_secondes = ?, total_repetitions = ?, statut = 'terminee'
        WHERE id = ?
        """, (duree_secondes, total_repetitions, seance_id))

        # Récupérer les infos de la séance
        seance = cursor.execute("SELECT * FROM seances_entrainement WHERE id = ?", (seance_id,)).fetchone()
        if not seance:
            conn.close()
            raise ValueError(f"Séance {seance_id} introuvable.")

        sportif_id = seance["sportif_id"]
        exercice_id = seance["exercice_id"]
        objectif_id = seance["objectif_id"]

        # 2. Insert repetitions (Composition 1-*)
        if repetitions:
            for r in repetitions:
                cursor.execute("""
                INSERT INTO repetitions (seance_id, numero, horodatage, duree_ms, amplitude, est_correcte)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    seance_id,
                    r.get("numero", 1),
                    r.get("horodatage", 0.0),
                    r.get("duree_ms", 0),
                    r.get("amplitude", 0.0),
                    1 if r.get("est_correcte", True) else 0
                ))

        # 3. Insert retours_correction (Composition 1-*)
        if corrections:
            for c in corrections:
                cursor.execute("""
                INSERT INTO retours_correction (seance_id, message, type, gravite, horodatage)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    seance_id,
                    c.get("message", ""),
                    c.get("type", "mixte"),
                    c.get("gravite", 1),
                    c.get("horodatage", 0.0)
                ))

        # 4. Vérification de l'atteinte des objectifs (verifierAtteinte)
        objectif_atteint = False
        notification_info = None

        # Recherche d'un objectif actif pour ce sportif et cet exercice
        query_obj = "SELECT * FROM objectifs WHERE sportif_id = ? AND exercice_id = ? AND atteint = 0"
        obj_row = cursor.execute(query_obj, (sportif_id, exercice_id)).fetchone()

        if obj_row:
            target_reps = obj_row["repetitions_cible"]
            # Total des répétitions récentes sur la période
            reps_cumulees = cursor.execute("""
            SELECT COALESCE(SUM(total_repetitions), 0) FROM seances_entrainement
            WHERE sportif_id = ? AND exercice_id = ? AND statut = 'terminee'
            """, (sportif_id, exercice_id)).fetchone()[0]

            if reps_cumulees >= target_reps or total_repetitions >= target_reps:
                objectif_atteint = True
                cursor.execute("UPDATE objectifs SET atteint = 1 WHERE id = ?", (obj_row["id"],))

                # Service de notification : créer la notification push pour le sportif
                msg = f"🎉 Félicitations ! Votre objectif de {target_reps} répétitions a été atteint avec succès !"
                cursor.execute("""
                INSERT INTO notifications (sportif_id, message, date_envoi, canal, statut)
                VALUES (?, ?, ?, 'push', 'non_lu')
                """, (sportif_id, msg, datetime.now().isoformat()))
                notification_id = cursor.lastrowid
                notification_info = {
                    "id": notification_id,
                    "message": msg,
                    "canal": "push"
                }

        conn.commit()
        conn.close()

        # Retourne le récapitulatif de séance
        recap = SeanceRepository.get_by_id(seance_id)
        return {
            "seance": recap,
            "objectif_atteint": objectif_atteint,
            "notification": notification_info
        }

    @staticmethod
    def get_by_id(seance_id: int) -> Optional[dict]:
        conn = get_connection()
        s = conn.execute("""
        SELECT s.*, e.nom as exercice_nom, e.groupe_musculaire, u.nom as sportif_nom, u.prenom as sportif_prenom, u.poids as sportif_poids
        FROM seances_entrainement s
        JOIN exercices e ON s.exercice_id = e.id
        JOIN utilisateurs u ON s.sportif_id = u.id
        WHERE s.id = ?
        """, (seance_id,)).fetchone()

        if not s:
            conn.close()
            return None

        reps = conn.execute("SELECT * FROM repetitions WHERE seance_id = ? ORDER BY numero ASC", (seance_id,)).fetchall()
        corrs = conn.execute("SELECT * FROM retours_correction WHERE seance_id = ? ORDER BY id ASC", (seance_id,)).fetchall()
        conn.close()

        # Calcul des calories (méthode métier)
        poids = s["sportif_poids"] or 70.0
        seance_metier = SeanceEntrainement(
            sportifId=s["sportif_id"],
            exerciceId=s["exercice_id"],
            idSeance=s["id"],
            dureeSecondes=s["duree_secondes"],
            totalRepetitions=s["total_repetitions"],
            statut=s["statut"]
        )
        calories = seance_metier.calculerCalories(poids)

        return {
            "id": s["id"],
            "sportif_id": s["sportif_id"],
            "sportif_nom": f"{s['sportif_prenom']} {s['sportif_nom']}",
            "exercice_id": s["exercice_id"],
            "exercice_nom": s["exercice_nom"],
            "groupe_musculaire": s["groupe_musculaire"],
            "objectif_id": s["objectif_id"],
            "date_debut": s["date_debut"],
            "duree_secondes": s["duree_secondes"],
            "statut": s["statut"],
            "total_repetitions": s["total_repetitions"],
            "calories_estimees": calories,
            "repetitions": [dict(r) for r in reps],
            "retours_correction": [dict(c) for c in corrs]
        }

    @staticmethod
    def get_historique_by_sportif(sportif_id: int) -> List[dict]:
        conn = get_connection()
        rows = conn.execute("""
        SELECT s.*, e.nom as exercice_nom, e.groupe_musculaire,
               (SELECT COUNT(*) FROM repetitions WHERE seance_id = s.id) as count_repetitions,
               (SELECT COUNT(*) FROM retours_correction WHERE seance_id = s.id) as count_corrections
        FROM seances_entrainement s
        JOIN exercices e ON s.exercice_id = e.id
        WHERE s.sportif_id = ?
        ORDER BY s.id DESC
        """, (sportif_id,)).fetchall()
        conn.close()

        historique = []
        for r in rows:
            seance_m = SeanceEntrainement(
                sportifId=r["sportif_id"],
                exerciceId=r["exercice_id"],
                dureeSecondes=r["duree_secondes"],
                totalRepetitions=r["total_repetitions"]
            )
            historique.append({
                "id": r["id"],
                "exercice_id": r["exercice_id"],
                "exercice_nom": r["exercice_nom"],
                "groupe_musculaire": r["groupe_musculaire"],
                "date_debut": r["date_debut"],
                "duree_secondes": r["duree_secondes"],
                "statut": r["statut"],
                "total_repetitions": r["total_repetitions"],
                "calories_estimees": seance_m.calculerCalories(70.0),
                "count_repetitions": r["count_repetitions"],
                "count_corrections": r["count_corrections"]
            })
        return historique


class ObjectifRepository:
    @staticmethod
    def get_by_sportif(sportif_id: int) -> List[dict]:
        conn = get_connection()
        rows = conn.execute("""
        SELECT o.*, e.nom as exercice_nom,
               COALESCE((
                   SELECT SUM(s.total_repetitions) 
                   FROM seances_entrainement s 
                   WHERE s.sportif_id = o.sportif_id AND s.exercice_id = o.exercice_id AND s.statut = 'terminee'
               ), 0) as total_actuel
        FROM objectifs o
        JOIN exercices e ON o.exercice_id = e.id
        WHERE o.sportif_id = ?
        ORDER BY o.id DESC
        """, (sportif_id,)).fetchall()
        conn.close()

        result = []
        for r in rows:
            obj_m = Objectif(
                sportifId=r["sportif_id"],
                exerciceId=r["exercice_id"],
                repetitionsCible=r["repetitions_cible"],
                periode=r["periode"],
                dateLimite=r["date_limite"],
                atteint=bool(r["atteint"])
            )
            progression = obj_m.calculerProgression(r["total_actuel"])
            result.append({
                "id": r["id"],
                "sportif_id": r["sportif_id"],
                "exercice_id": r["exercice_id"],
                "exercice_nom": r["exercice_nom"],
                "repetitions_cible": r["repetitions_cible"],
                "periode": r["periode"],
                "date_limite": r["date_limite"],
                "atteint": bool(r["atteint"]),
                "total_actuel": r["total_actuel"],
                "progression_pourcentage": progression
            })
        return result

    @staticmethod
    def create(sportif_id: int, exercice_id: int, repetitions_cible: int, periode: str, date_limite: str) -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO objectifs (sportif_id, exercice_id, repetitions_cible, periode, date_limite, atteint)
        VALUES (?, ?, ?, ?, ?, 0)
        """, (sportif_id, exercice_id, repetitions_cible, periode, date_limite))
        conn.commit()
        obj_id = cursor.lastrowid
        conn.close()
        return {"id": obj_id, "message": "Objectif créé avec succès"}


class NotificationRepository:
    @staticmethod
    def get_by_sportif(sportif_id: int) -> List[dict]:
        conn = get_connection()
        rows = conn.execute("""
        SELECT * FROM notifications 
        WHERE sportif_id = ? 
        ORDER BY id DESC
        """, (sportif_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def mark_all_read(sportif_id: int):
        conn = get_connection()
        conn.execute("UPDATE notifications SET statut = 'lu' WHERE sportif_id = ?", (sportif_id,))
        conn.commit()
        conn.close()


class AdminRepository:
    @staticmethod
    def get_all_users() -> List[dict]:
        conn = get_connection()
        rows = conn.execute("""
        SELECT id, nom, prenom, email, date_inscription, role, poids, taille, niveau, niveau_acces,
               (SELECT COUNT(*) FROM seances_entrainement WHERE sportif_id = utilisateurs.id) as nb_seances,
               (SELECT COALESCE(SUM(total_repetitions), 0) FROM seances_entrainement WHERE sportif_id = utilisateurs.id) as total_reps
        FROM utilisateurs
        ORDER BY id ASC
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def update_role(user_id: int, role: str, niveau_acces: int = 1) -> bool:
        conn = get_connection()
        conn.execute("UPDATE utilisateurs SET role = ?, niveau_acces = ? WHERE id = ?", (role, niveau_acces, user_id))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def get_global_statistics() -> Dict[str, Any]:
        conn = get_connection()
        cursor = conn.cursor()

        nb_users = cursor.execute("SELECT COUNT(*) FROM utilisateurs").fetchone()[0]
        nb_sportifs = cursor.execute("SELECT COUNT(*) FROM utilisateurs WHERE role = 'sportif'").fetchone()[0]
        nb_seances = cursor.execute("SELECT COUNT(*) FROM seances_entrainement").fetchone()[0]
        total_reps = cursor.execute("SELECT COALESCE(SUM(total_repetitions), 0) FROM seances_entrainement").fetchone()[0]
        total_duree = cursor.execute("SELECT COALESCE(SUM(duree_secondes), 0) FROM seances_entrainement").fetchone()[0]
        nb_corrections = cursor.execute("SELECT COUNT(*) FROM retours_correction").fetchone()[0]

        # Répartition par exercice
        exos_stat = cursor.execute("""
        SELECT e.nom, COUNT(s.id) as nb_seances, COALESCE(SUM(s.total_repetitions), 0) as total_reps
        FROM exercices e
        LEFT JOIN seances_entrainement s ON e.id = s.exercice_id
        GROUP BY e.id, e.nom
        ORDER BY total_reps DESC
        """).fetchall()

        # Objectifs
        total_objectifs = cursor.execute("SELECT COUNT(*) FROM objectifs").fetchone()[0]
        objectifs_atteints = cursor.execute("SELECT COUNT(*) FROM objectifs WHERE atteint = 1").fetchone()[0]

        conn.close()

        taux_reussite = round((objectifs_atteints / total_objectifs * 100.0), 1) if total_objectifs > 0 else 0.0

        return {
            "total_utilisateurs": nb_users,
            "total_sportifs": nb_sportifs,
            "total_seances": nb_seances,
            "total_repetitions": total_reps,
            "duree_totale_minutes": round(total_duree / 60.0, 1),
            "total_corrections_emises": nb_corrections,
            "total_objectifs": total_objectifs,
            "objectifs_atteints": objectifs_atteints,
            "taux_reussite_objectifs": taux_reussite,
            "exercices_populaires": [dict(e) for e in exos_stat]
        }
