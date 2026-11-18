"""
SeanceEntrainement - Représente une séance d'entraînement réalisée par un sportif sur un exercice donné.
Compositions :
- 1-* Repetition (les répétitions sont supprimées avec la séance)
- 1-* RetourCorrection (les corrections sont rattachées à la séance)
Associations :
- 1-1 MoteurVision
- 1-1 CompteurRepetitions
- *->1 Exercice
"""
import time
from datetime import datetime
from typing import Optional, List
from domain.repetition import Repetition
from domain.retour_correction import RetourCorrection
from domain.moteur_vision import MoteurVision
from domain.compteur_repetitions import CompteurRepetitions
from domain.exercice import Exercice


class SeanceEntrainement:
    def __init__(
        self,
        sportifId: int,
        exerciceId: int,
        idSeance: Optional[int] = None,
        objectifId: Optional[int] = None,
        dateDebut: Optional[str] = None,
        dureeSecondes: int = 0,
        statut: str = "en_cours",
        totalRepetitions: int = 0
    ):
        self.idSeance = idSeance
        self.sportifId = int(sportifId)
        self.exerciceId = int(exerciceId)
        self.objectifId = int(objectifId) if objectifId is not None else None
        self.dateDebut = dateDebut or datetime.now().isoformat()
        self.dureeSecondes = int(dureeSecondes)
        self.statut = statut  # 'en_cours', 'en_pause', 'terminee'
        self.totalRepetitions = int(totalRepetitions)

        # Compositions
        self.repetitions: List[Repetition] = []
        self.retoursCorrection: List[RetourCorrection] = []

        # Instances d'exécution
        self.moteurVision: Optional[MoteurVision] = None
        self.compteurRepetitions: Optional[CompteurRepetitions] = None
        self._tempsDebutChrono = time.time()
        self._tempsPauseDebut = 0.0

    def attacherMoteur(self, moteur: MoteurVision) -> None:
        """Associe le moteur de vision et le compteur à cette séance."""
        self.moteurVision = moteur
        self.compteurRepetitions = moteur.getCompteur()

    def demarrer(self) -> None:
        """Démarre la séance et le chronomètre."""
        self.statut = "en_cours"
        self._tempsDebutChrono = time.time()

    def mettreEnPause(self) -> None:
        """Met en pause la séance et suspend le moteur de vision."""
        if self.statut == "en_cours":
            self.statut = "en_pause"
            self._tempsPauseDebut = time.time()
            if self.moteurVision:
                self.moteurVision.suspendre()

    def reprendre(self) -> None:
        """Reprend la séance mise en pause."""
        if self.statut == "en_pause":
            self.statut = "en_cours"
            if self._tempsPauseDebut > 0:
                temps_pause = time.time() - self._tempsPauseDebut
                self._tempsDebutChrono += temps_pause
                self._tempsPauseDebut = 0.0
            if self.moteurVision:
                self.moteurVision.reprendre()

    def terminer(self) -> None:
        """Clôture la séance, calcule la durée finale et synchronise le total."""
        self.statut = "terminee"
        if self.dureeSecondes == 0 and self._tempsDebutChrono > 0:
            self.dureeSecondes = int(time.time() - self._tempsDebutChrono)
        if self.compteurRepetitions:
            self.totalRepetitions = self.compteurRepetitions.getTotal()
            self.repetitions = list(self.compteurRepetitions.historiqueRepetitions)
            self.retoursCorrection = list(self.compteurRepetitions.historiqueCorrections)
        if self.moteurVision:
            self.moteurVision.suspendre()

    def calculerCalories(self, poids_kg: float = 70.0) -> float:
        """
        Calcule une estimation calorique réaliste basée sur :
        - Le type d'exercice et son coût métabolique (MET)
        - Le total de répétitions et la durée
        - Le poids de l'athlète (défaut: 70kg)
        Formule : Calories = (MET * 3.5 * poids / 200) * (durée en minutes) + (reps * coef)
        """
        # Estimation simplifiée standardisée
        coef_par_rep = 0.35  # ~ 0.35 kcal par répétition en moyenne
        calories_reps = self.totalRepetitions * coef_par_rep
        duree_minutes = max(1.0, self.dureeSecondes / 60.0)
        calories_temps = (duree_minutes * 4.5 * 3.5 * (poids_kg / 70.0)) / 10.0
        return round(calories_reps + calories_temps, 1)

    def to_dict(self) -> dict:
        return {
            "id": self.idSeance,
            "sportif_id": self.sportifId,
            "exercice_id": self.exerciceId,
            "objectif_id": self.objectifId,
            "date_debut": self.dateDebut,
            "duree_secondes": self.dureeSecondes,
            "statut": self.statut,
            "total_repetitions": self.totalRepetitions,
            "calories_estimees": self.calculerCalories(),
            "repetitions": [r.to_dict() for r in self.repetitions],
            "retours_correction": [c.to_dict() for c in self.retoursCorrection]
        }
