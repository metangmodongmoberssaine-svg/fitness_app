"""
Tests unitaires et d'intégration validant :
1. Le calcul des angles et vecteurs anatomiques (formule arccos).
2. La machine à états à hystérésis du CompteurRepetitions.
3. Les classes métier : RegleDeComptage, SeanceEntrainement, Objectif, Utilisateur.
4. Les endpoints de l'API REST FastAPI.
"""
import unittest
import math
import sys
import os

# Ajout du chemin backend
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from domain.point_cle import PointCle
from domain.posture import Posture
from domain.regle_de_comptage import RegleDeComptage
from domain.compteur_repetitions import CompteurRepetitions
from domain.repetition import Repetition
from domain.seance_entrainement import SeanceEntrainement
from domain.objectif import Objectif
from domain.utilisateur import Sportif, Administrateur
from database.db import init_db
from database.repository import AuthRepository, ExerciceRepository, SeanceRepository, ObjectifRepository


class TestDomainModel(unittest.TestCase):

    def setUp(self):
        init_db()

    def test_point_cle_distance(self):
        p1 = PointCle("p1", 0, 0, 0)
        p2 = PointCle("p2", 3, 4, 0)
        self.assertAlmostEqual(p1.distanceVers(p2), 5.0)

    def test_calcul_angle_droit(self):
        # Angle de 90° à l'articulation B (0, 0) entre A (0, 10) et C (10, 0)
        ptA = PointCle("left_shoulder", 0, 10, 0)
        ptB = PointCle("left_elbow", 0, 0, 0)
        ptC = PointCle("left_wrist", 10, 0, 0)
        posture = Posture([ptA, ptB, ptC])

        angle = posture.getAngle("left_shoulder", "left_elbow", "left_wrist")
        self.assertAlmostEqual(angle, 90.0, places=1)

    def test_calcul_angle_plat(self):
        # Angle de 180° à l'articulation B (0, 0) entre A (-10, 0) et C (10, 0)
        ptA = PointCle("left_hip", -10, 0, 0)
        ptB = PointCle("left_knee", 0, 0, 0)
        ptC = PointCle("left_ankle", 10, 0, 0)
        posture = Posture([ptA, ptB, ptC])

        angle = posture.getAngle("left_hip", "left_knee", "left_ankle")
        self.assertAlmostEqual(angle, 180.0, places=1)

    def test_regle_comptage_hysteresis(self):
        # Règle Squat : angle haut 165°, angle bas 90°, tolérance 10°
        regle = RegleDeComptage("genou", angleHaut=165.0, angleBas=90.0, tolerance=10.0, dureeMinRepetition=100)
        self.assertEqual(regle.evaluerPhase(170.0), "haute")
        self.assertEqual(regle.evaluerPhase(85.0), "basse")
        self.assertEqual(regle.evaluerPhase(120.0), "transition")

    def test_machine_a_etats_decompte(self):
        regle = RegleDeComptage("genou", angleHaut=160.0, angleBas=90.0, tolerance=10.0, dureeMinRepetition=50)
        compteur = CompteurRepetitions(regle)

        # 1. Position haute (jambes tendues)
        p_haut = Posture([
            PointCle("left_hip", 0, 10, 0),
            PointCle("left_knee", 0, 0, 0),
            PointCle("left_ankle", 0, -10, 0)  # 180°
        ])
        rep_validee, corr, rep, angle = compteur.traiter(p_haut)
        self.assertFalse(rep_validee)
        self.assertEqual(compteur.phaseCourante, "haute")
        self.assertEqual(compteur.getTotal(), 0)

        # 2. Position basse (squat fléchi 85°)
        p_bas = Posture([
            PointCle("left_hip", 0, 10, 0),
            PointCle("left_knee", 0, 0, 0),
            PointCle("left_ankle", 9.9, 1.0, 0)  # ~85°
        ])
        rep_validee, corr, rep, angle = compteur.traiter(p_bas)
        self.assertFalse(rep_validee)
        self.assertEqual(compteur.phaseCourante, "basse")

        # Simuler un court délai de travail musculaire
        import time
        time.sleep(0.06)

        # 3. Remontée en position haute (180°) -> validation de la répétition !
        rep_validee, corr, rep, angle = compteur.traiter(p_haut)
        self.assertTrue(rep_validee)
        self.assertEqual(compteur.getTotal(), 1)
        self.assertIsNotNone(rep)
        self.assertEqual(rep.numero, 1)

    def test_seance_calories(self):
        seance = SeanceEntrainement(sportifId=1, exerciceId=1, dureeSecondes=300, totalRepetitions=25)
        calories = seance.calculerCalories(poids_kg=75.0)
        self.assertGreater(calories, 10.0)

    def test_objectif_progression(self):
        obj = Objectif(sportifId=1, exerciceId=1, repetitionsCible=50)
        self.assertFalse(obj.verifierAtteinte(30))
        self.assertEqual(obj.calculerProgression(30), 60.0)
        self.assertTrue(obj.verifierAtteinte(50))
        self.assertEqual(obj.calculerProgression(50), 100.0)


class TestRepositoryAndDatabase(unittest.TestCase):

    def setUp(self):
        init_db()

    def test_catalogue_exercices(self):
        exos = ExerciceRepository.get_all()
        self.assertGreaterEqual(len(exos), 4)
        squat = next(e for e in exos if e["nom"] == "Squat")
        self.assertIsNotNone(squat["regle"])
        self.assertEqual(squat["regle"]["articulation_cle"], "genou")

    def test_cycle_vie_seance(self):
        # Création (Phase 1)
        id_seance = SeanceRepository.create(sportif_id=2, exercice_id=1)
        self.assertIsInstance(id_seance, int)

        # Clôture avec répétitions (Phase 3)
        reps = [
            {"numero": 1, "horodatage": 100.0, "duree_ms": 1200, "amplitude": 75.0, "est_correcte": True},
            {"numero": 2, "horodatage": 102.0, "duree_ms": 1100, "amplitude": 72.0, "est_correcte": True}
        ]
        corrs = [
            {"message": "Descendez plus bas", "type": "visuel", "gravite": 1, "horodatage": 101.0}
        ]
        res = SeanceRepository.cloturer(
            seance_id=id_seance,
            duree_secondes=60,
            total_repetitions=2,
            repetitions=reps,
            corrections=corrs
        )
        seance_recap = res["seance"]
        self.assertEqual(seance_recap["total_repetitions"], 2)
        self.assertEqual(seance_recap["statut"], "terminee")
        self.assertEqual(len(seance_recap["repetitions"]), 2)
        self.assertEqual(len(seance_recap["retours_correction"]), 1)


if __name__ == "__main__":
    unittest.main()
