-- ============================================================
-- AI Fitness Counter : création manuelle de la base MySQL
-- À importer dans phpMyAdmin (onglet SQL) ou :
--     mysql -u root -p < schema_mysql.sql
-- (Facultatif : l'application crée déjà ces tables toute seule.)
-- ============================================================
CREATE DATABASE IF NOT EXISTS `fitness_counter_db`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `fitness_counter_db`;

CREATE TABLE IF NOT EXISTS utilisateurs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nom VARCHAR(100) NOT NULL,
  prenom VARCHAR(100) NOT NULL,
  email VARCHAR(191) UNIQUE NOT NULL,
  mot_de_passe_hash VARCHAR(255) NOT NULL,
  date_inscription VARCHAR(50) NOT NULL,
  role ENUM('sportif','administrateur') NOT NULL DEFAULT 'sportif',
  poids DOUBLE DEFAULT 70.0,
  taille DOUBLE DEFAULT 175.0,
  niveau VARCHAR(50) DEFAULT 'Intermédiaire',
  niveau_acces INT DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS exercices (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nom VARCHAR(100) NOT NULL,
  description TEXT NOT NULL,
  groupe_musculaire VARCHAR(100) NOT NULL,
  difficulte INT NOT NULL DEFAULT 1,
  video_sample VARCHAR(255) DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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

CREATE TABLE IF NOT EXISTS retours_correction (
  id INT AUTO_INCREMENT PRIMARY KEY,
  seance_id INT NOT NULL,
  message VARCHAR(255) NOT NULL,
  type VARCHAR(30) NOT NULL DEFAULT 'mixte',
  gravite INT NOT NULL DEFAULT 1,
  horodatage DOUBLE NULL,
  CONSTRAINT fk_corr_seance FOREIGN KEY (seance_id) REFERENCES seances_entrainement(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS notifications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  sportif_id INT NOT NULL,
  message VARCHAR(255) NOT NULL,
  date_envoi VARCHAR(50) NOT NULL,
  canal VARCHAR(30) NOT NULL DEFAULT 'push',
  statut VARCHAR(30) NOT NULL DEFAULT 'non_lu',
  CONSTRAINT fk_notif_sportif FOREIGN KEY (sportif_id) REFERENCES utilisateurs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------- Ajouts : vidéos d'exercices (admin) et calendrier d'entraînement ----------
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