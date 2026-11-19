"""
Module de Persistance MySQL & SQLite.
Implémente le schéma relationnel conforme au Dossier de Conception UML (Section 3.7 & Page 19).
Base par défaut : MySQL (WampServer / MariaDB) sur 127.0.0.1:3306 avec base 'fitness_counter_db'.
Fallback transparent vers SQLite si MySQL est indisponible.
"""
import os
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime

# Paramètres de configuration de connexion MySQL
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "fitness_counter_db")

# Détection disponibilité MySQL
USE_MYSQL = True
try:
    import pymysql
    import pymysql.cursors
except ImportError:
    USE_MYSQL = False

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "fitness_counter.db")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class RowDict(dict):
    """Dictionnaire permettant l'accès par clé str ET par index int (comme sqlite3.Row)."""
    def __getitem__(self, item):
        if isinstance(item, int):
            return list(self.values())[item]
        return super().__getitem__(item)


class CursorWrapper:
    """Encapsule un curseur MySQL ou SQLite pour uniformiser les requêtes, placeholders et formats de retour."""
    def __init__(self, raw_cursor, is_mysql=True):
        self.cur = raw_cursor
        self.is_mysql = is_mysql

    def execute(self, query: str, params: tuple = ()):
        if self.is_mysql:
            query = query.replace("?", "%s")
        else:
            query = query.replace("%s", "?")
        self.cur.execute(query, params)
        return self

    def fetchone(self):
        r = self.cur.fetchone()
        if r is not None and isinstance(r, dict):
            return RowDict(r)
        return r

    def fetchall(self):
        rows = self.cur.fetchall()
        if rows and isinstance(rows, (list, tuple)) and len(rows) > 0 and isinstance(rows[0], dict):
            return [RowDict(r) for r in rows]
        return rows

    @property
    def lastrowid(self):
        return self.cur.lastrowid

    @property
    def rowcount(self):
        return self.cur.rowcount

    def close(self):
        self.cur.close()

    def __iter__(self):
        return iter(self.cur)


class DatabaseConnection:
    """Wrapper uniforme gérant les différences subtiles de curseurs entre MySQL et SQLite."""
    def __init__(self, is_mysql=True, conn=None):
        self.is_mysql = is_mysql
        self.conn = conn

    def cursor(self):
        if self.is_mysql:
            return CursorWrapper(self.conn.cursor(pymysql.cursors.DictCursor), is_mysql=True)
        else:
            return CursorWrapper(self.conn.cursor(), is_mysql=False)

    def execute(self, query: str, params: tuple = ()):
        cur = self.cursor()
        cur.execute(query, params)
        return cur

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


def get_connection() -> DatabaseConnection:
    global USE_MYSQL
    if USE_MYSQL:
        try:
            raw_conn = pymysql.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset="utf8mb4",
                autocommit=False
            )
            return DatabaseConnection(is_mysql=True, conn=raw_conn)
        except Exception as e:
            print(f"[Avertissement MySQL] Connexion impossible sur {DB_HOST}:{DB_PORT} ({e}). Basculement sur SQLite.")

    # Fallback SQLite
    import sqlite3
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return DatabaseConnection(is_mysql=False, conn=conn)


def init_db():
    """Initialise la base de données, crée les tables et injecte les données de démarrage."""
    global USE_MYSQL
    # 1. Si MySQL, s'assurer que la base de données existe
    if USE_MYSQL:
        try:
            admin_conn = pymysql.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                charset="utf8mb4"
            )
            with admin_conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            admin_conn.commit()
            admin_conn.close()
        except Exception as e:
            print(f"[MySQL Init] Erreur création de la base: {e}")

    db = get_connection()
    cur = db.cursor()
    print(f"[Base de données] Moteur utilisé : {'MySQL ' + DB_NAME if db.is_mysql else 'SQLite (fichier local)'}")

    # DDL compatible MySQL & SQLite
    if db.is_mysql:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nom VARCHAR(100) NOT NULL,
            prenom VARCHAR(100) NOT NULL,
            email VARCHAR(191) UNIQUE NOT NULL,
            mot_de_passe_hash VARCHAR(255) NOT NULL,
            date_inscription VARCHAR(50) NOT NULL,
            role ENUM('sportif', 'administrateur') NOT NULL DEFAULT 'sportif',
            poids DOUBLE DEFAULT 70.0,
            taille DOUBLE DEFAULT 175.0,
            niveau VARCHAR(50) DEFAULT 'Intermédiaire',
            niveau_acces INT DEFAULT 1
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS exercices (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nom VARCHAR(100) NOT NULL,
            description TEXT NOT NULL,
            groupe_musculaire VARCHAR(100) NOT NULL,
            difficulte INT NOT NULL DEFAULT 1,
            video_sample VARCHAR(255) DEFAULT ''
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS regles_comptage (
            id INT AUTO_INCREMENT PRIMARY KEY,
            exercice_id INT UNIQUE NOT NULL,
            articulation_cle VARCHAR(50) NOT NULL,
            angle_haut DOUBLE NOT NULL,
            angle_bas DOUBLE NOT NULL,
            tolerance DOUBLE NOT NULL DEFAULT 10.0,
            duree_min_repetition INT NOT NULL DEFAULT 600,
            CONSTRAINT fk_regle_exercice FOREIGN KEY (exercice_id) REFERENCES exercices(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS objectifs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            sportif_id INT NOT NULL,
            exercice_id INT NOT NULL,
            repetitions_cible INT NOT NULL,
            periode VARCHAR(50) NOT NULL DEFAULT 'quotidien',
            date_limite VARCHAR(50) DEFAULT '',
            atteint TINYINT(1) NOT NULL DEFAULT 0,
            CONSTRAINT fk_obj_sportif FOREIGN KEY (sportif_id) REFERENCES utilisateurs(id) ON DELETE CASCADE,
            CONSTRAINT fk_obj_exercice FOREIGN KEY (exercice_id) REFERENCES exercices(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS seances_entrainement (
            id INT AUTO_INCREMENT PRIMARY KEY,
            sportif_id INT NOT NULL,
            exercice_id INT NOT NULL,
            objectif_id INT NULL,
            date_debut VARCHAR(50) NOT NULL,
            duree_secondes INT NOT NULL DEFAULT 0,
            statut VARCHAR(30) NOT NULL DEFAULT 'en_cours',
            total_repetitions INT NOT NULL DEFAULT 0,
            CONSTRAINT fk_seance_sportif FOREIGN KEY (sportif_id) REFERENCES utilisateurs(id) ON DELETE CASCADE,
            CONSTRAINT fk_seance_exercice FOREIGN KEY (exercice_id) REFERENCES exercices(id) ON DELETE CASCADE,
            CONSTRAINT fk_seance_objectif FOREIGN KEY (objectif_id) REFERENCES objectifs(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS repetitions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            seance_id INT NOT NULL,
            numero INT NOT NULL,
            horodatage DOUBLE NOT NULL,
            duree_ms INT NOT NULL,
            amplitude DOUBLE NOT NULL,
            est_correcte TINYINT(1) NOT NULL DEFAULT 1,
            CONSTRAINT fk_rep_seance FOREIGN KEY (seance_id) REFERENCES seances_entrainement(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS retours_correction (
            id INT AUTO_INCREMENT PRIMARY KEY,
            seance_id INT NOT NULL,
            message VARCHAR(255) NOT NULL,
            type VARCHAR(30) NOT NULL DEFAULT 'mixte',
            gravite INT NOT NULL DEFAULT 1,
            horodatage DOUBLE NULL,
            CONSTRAINT fk_corr_seance FOREIGN KEY (seance_id) REFERENCES seances_entrainement(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            sportif_id INT NOT NULL,
            message VARCHAR(255) NOT NULL,
            date_envoi VARCHAR(50) NOT NULL,
            canal VARCHAR(30) NOT NULL DEFAULT 'push',
            statut VARCHAR(30) NOT NULL DEFAULT 'non_lu',
            CONSTRAINT fk_notif_sportif FOREIGN KEY (sportif_id) REFERENCES utilisateurs(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS videos_exercices (
            id INT AUTO_INCREMENT PRIMARY KEY,
            exercice_id INT NOT NULL,
            titre VARCHAR(150) NOT NULL DEFAULT '',
            chemin VARCHAR(255) NOT NULL,
            taille_octets BIGINT NOT NULL DEFAULT 0,
            uploaded_by INT NULL,
            date_ajout VARCHAR(50) NOT NULL,
            CONSTRAINT fk_video_exercice FOREIGN KEY (exercice_id) REFERENCES exercices(id) ON DELETE CASCADE,
            CONSTRAINT fk_video_user FOREIGN KEY (uploaded_by) REFERENCES utilisateurs(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS planifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            sportif_id INT NOT NULL,
            exercice_id INT NOT NULL,
            date_prevue VARCHAR(10) NOT NULL,
            heure VARCHAR(5) NOT NULL DEFAULT '18:00',
            note VARCHAR(255) DEFAULT '',
            statut VARCHAR(20) NOT NULL DEFAULT 'prevue',
            CONSTRAINT fk_plan_sportif FOREIGN KEY (sportif_id) REFERENCES utilisateurs(id) ON DELETE CASCADE,
            CONSTRAINT fk_plan_exercice FOREIGN KEY (exercice_id) REFERENCES exercices(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

    else:
        # Tables SQLite
        cur.execute("""
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            mot_de_passe_hash TEXT NOT NULL,
            date_inscription TEXT NOT NULL,
            role TEXT NOT NULL,
            poids REAL DEFAULT 70.0,
            taille REAL DEFAULT 175.0,
            niveau TEXT DEFAULT 'Intermédiaire',
            niveau_acces INTEGER DEFAULT 1
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS exercices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            description TEXT NOT NULL,
            groupe_musculaire TEXT NOT NULL,
            difficulte INTEGER NOT NULL DEFAULT 1,
            video_sample TEXT DEFAULT ''
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS regles_comptage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercice_id INTEGER UNIQUE NOT NULL,
            articulation_cle TEXT NOT NULL,
            angle_haut REAL NOT NULL,
            angle_bas REAL NOT NULL,
            tolerance REAL NOT NULL DEFAULT 10.0,
            duree_min_repetition INTEGER NOT NULL DEFAULT 600,
            FOREIGN KEY (exercice_id) REFERENCES exercices(id) ON DELETE CASCADE
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS objectifs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sportif_id INTEGER NOT NULL,
            exercice_id INTEGER NOT NULL,
            repetitions_cible INTEGER NOT NULL,
            periode TEXT NOT NULL DEFAULT 'quotidien',
            date_limite TEXT,
            atteint BOOLEAN NOT NULL DEFAULT 0,
            FOREIGN KEY (sportif_id) REFERENCES utilisateurs(id) ON DELETE CASCADE,
            FOREIGN KEY (exercice_id) REFERENCES exercices(id) ON DELETE CASCADE
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS seances_entrainement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sportif_id INTEGER NOT NULL,
            exercice_id INTEGER NOT NULL,
            objectif_id INTEGER,
            date_debut TEXT NOT NULL,
            duree_secondes INTEGER NOT NULL DEFAULT 0,
            statut TEXT NOT NULL DEFAULT 'en_cours',
            total_repetitions INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (sportif_id) REFERENCES utilisateurs(id) ON DELETE CASCADE,
            FOREIGN KEY (exercice_id) REFERENCES exercices(id) ON DELETE CASCADE,
            FOREIGN KEY (objectif_id) REFERENCES objectifs(id) ON DELETE SET NULL
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS repetitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seance_id INTEGER NOT NULL,
            numero INTEGER NOT NULL,
            horodatage REAL NOT NULL,
            duree_ms INTEGER NOT NULL,
            amplitude REAL NOT NULL,
            est_correcte BOOLEAN NOT NULL DEFAULT 1,
            FOREIGN KEY (seance_id) REFERENCES seances_entrainement(id) ON DELETE CASCADE
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS retours_correction (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seance_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'mixte',
            gravite INTEGER NOT NULL DEFAULT 1,
            horodatage REAL,
            FOREIGN KEY (seance_id) REFERENCES seances_entrainement(id) ON DELETE CASCADE
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sportif_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            date_envoi TEXT NOT NULL,
            canal TEXT NOT NULL DEFAULT 'push',
            statut TEXT NOT NULL DEFAULT 'non_lu',
            FOREIGN KEY (sportif_id) REFERENCES utilisateurs(id) ON DELETE CASCADE
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS videos_exercices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercice_id INTEGER NOT NULL,
            titre TEXT NOT NULL DEFAULT '',
            chemin TEXT NOT NULL,
            taille_octets INTEGER NOT NULL DEFAULT 0,
            uploaded_by INTEGER,
            date_ajout TEXT NOT NULL,
            FOREIGN KEY (exercice_id) REFERENCES exercices(id) ON DELETE CASCADE,
            FOREIGN KEY (uploaded_by) REFERENCES utilisateurs(id) ON DELETE SET NULL
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS planifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sportif_id INTEGER NOT NULL,
            exercice_id INTEGER NOT NULL,
            date_prevue TEXT NOT NULL,
            heure TEXT NOT NULL DEFAULT '18:00',
            note TEXT DEFAULT '',
            statut TEXT NOT NULL DEFAULT 'prevue',
            FOREIGN KEY (sportif_id) REFERENCES utilisateurs(id) ON DELETE CASCADE,
            FOREIGN KEY (exercice_id) REFERENCES exercices(id) ON DELETE CASCADE
        );
        """)

    db.commit()
    seed_initial_data(db)
    db.close()


def seed_initial_data(db: DatabaseConnection):
    cur = db.cursor()

    # Utilisateurs de test
    cur.execute("SELECT COUNT(*) as cnt FROM utilisateurs")
    row = cur.fetchone()
    cnt = row["cnt"] if isinstance(row, dict) else row[0]

    if cnt == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sql_users = """
        INSERT INTO utilisateurs (nom, prenom, email, mot_de_passe_hash, date_inscription, role, poids, taille, niveau, niveau_acces)
        VALUES 
        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s),
        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s),
        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params_users = (
            'Admin', 'Super', 'admin@fitness.ai', hash_password("admin123"), now_str, 'administrateur', 75.0, 180.0, 'Expert', 2,
            'Dupont', 'Jean', 'jean@fitness.ai', hash_password("sportif123"), now_str, 'sportif', 74.5, 178.0, 'Intermédiaire', 1,
            'Martin', 'Sophie', 'sophie@fitness.ai', hash_password("sportif123"), now_str, 'sportif', 62.0, 166.0, 'Débutant', 1
        )
        if not db.is_mysql:
            sql_users = sql_users.replace("%s", "?")
        cur.execute(sql_users, params_users)

    # Exercices & Règles
    cur.execute("SELECT COUNT(*) as cnt FROM exercices")
    row = cur.fetchone()
    cnt = row["cnt"] if isinstance(row, dict) else row[0]

    if cnt == 0:
        exercices_data = [
            (
                "Squat",
                "Flexion des jambes pour solliciter quadriceps, fessiers et ischios-jambiers. Descendez jusqu'à ce que les cuisses soient parallèles au sol.",
                "Jambes & Fessiers",
                1,
                "/samples/squat.mp4",
                ("genou", 165.0, 90.0, 12.0, 750)
            ),
            (
                "Pompe (Push-up)",
                "Flexion et extension des bras au sol. Gainage complet du tronc, descente de la poitrine près du sol puis extension complète.",
                "Pectoraux, Épaules & Triceps",
                2,
                "/samples/pushup.mp4",
                ("coude", 160.0, 90.0, 12.0, 650)
            ),
            (
                "Dumbbell Curl (Biceps)",
                "Flexion de l'avant-bras avec haltère. Gardez les coudes collés au buste sans balancement du dos.",
                "Bras & Biceps",
                1,
                "/samples/dumbbell workout.mp4",
                ("coude", 160.0, 100.0, 12.0, 600)
            ),
            (
                "Chest Fly Machine",
                "Écarté à la machine pectoraux. Rapprochement contrôlé des poignets vers le centre de la poitrine.",
                "Pectoraux",
                2,
                "/samples/chest fly machine.mp4",
                ("distance_poignets", 260.0, 110.0, 20.0, 700)
            ),
            (
                "Traction (Pull-up)",
                "Suspension à la barre fixe et traction du corps jusqu'à ce que le menton dépasse la barre.",
                "Dos & Biceps",
                3,
                "",
                ("coude", 165.0, 75.0, 10.0, 900)
            )
        ]

        for nom, desc, groupe, diff, video, regle in exercices_data:
            q_exo = "INSERT INTO exercices (nom, description, groupe_musculaire, difficulte, video_sample) VALUES (%s, %s, %s, %s, %s)"
            if not db.is_mysql:
                q_exo = q_exo.replace("%s", "?")
            cur.execute(q_exo, (nom, desc, groupe, diff, video))
            exo_id = cur.lastrowid
            art, a_haut, a_bas, tol, duree = regle
            q_regle = "INSERT INTO regles_comptage (exercice_id, articulation_cle, angle_haut, angle_bas, tolerance, duree_min_repetition) VALUES (%s, %s, %s, %s, %s, %s)"
            if not db.is_mysql:
                q_regle = q_regle.replace("%s", "?")
            cur.execute(q_regle, (exo_id, art, a_haut, a_bas, tol, duree))

    # Objectifs de test
    cur.execute("SELECT COUNT(*) as cnt FROM objectifs")
    row = cur.fetchone()
    cnt = row["cnt"] if isinstance(row, dict) else row[0]

    if cnt == 0:
        q_obj = "INSERT INTO objectifs (sportif_id, exercice_id, repetitions_cible, periode, date_limite, atteint) VALUES (%s, %s, %s, %s, %s, %s)"
        if not db.is_mysql:
            q_obj = q_obj.replace("%s", "?")
        cur.execute(q_obj, (2, 1, 20, 'quotidien', '2026-12-31', 0))
        cur.execute(q_obj, (2, 2, 15, 'hebdomadaire', '2026-12-31', 0))

    # Notifications de test
    cur.execute("SELECT COUNT(*) as cnt FROM notifications")
    row = cur.fetchone()
    cnt = row["cnt"] if isinstance(row, dict) else row[0]

    if cnt == 0:
        q_notif = "INSERT INTO notifications (sportif_id, message, date_envoi, canal, statut) VALUES (%s, %s, %s, %s, %s)"
        if not db.is_mysql:
            q_notif = q_notif.replace("%s", "?")
        cur.execute(q_notif, (2, 'Bienvenue sur votre coach IA en temps réel ! Vos objectifs sont prêts.', datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'push', 'non_lu'))

    db.commit()