"""
Objectif - Cible de répétitions à atteindre sur une période donnée (quotidien, hebdomadaire, etc.).
Relations :
- Sportif Composition 1-* Objectif (disparaît avec le compte du sportif)
- Objectif *->1 Exercice (porte sur un exercice précis)
- Objectif Agrégation 0..1-* SeanceEntrainement (regroupe plusieurs séances sans les détruire)
"""
from typing import Optional


class Objectif:
    def __init__(
        self,
        sportifId: int,
        exerciceId: int,
        repetitionsCible: int,
        periode: str = "quotidien",
        dateLimite: str = "",
        atteint: bool = False,
        idObjectif: Optional[int] = None
    ):
        self.idObjectif = idObjectif
        self.sportifId = int(sportifId)
        self.exerciceId = int(exerciceId)
        self.repetitionsCible = int(repetitionsCible)
        self.periode = periode
        self.dateLimite = dateLimite
        self.atteint = bool(atteint)

    def verifierAtteinte(self, total: int) -> bool:
        """
        Vérifie si le total de répétitions accumulé atteint ou dépasse la cible.
        Met à jour l'attribut atteint.
        """
        if total >= self.repetitionsCible:
            self.atteint = True
            return True
        return False

    def calculerProgression(self, totalActuel: int) -> float:
        """Calcule le pourcentage de progression vers la cible (0 à 100%)."""
        if self.repetitionsCible <= 0:
            return 100.0
        pourcentage = (totalActuel / self.repetitionsCible) * 100.0
        return round(min(100.0, max(0.0, pourcentage)), 1)

    def to_dict(self) -> dict:
        return {
            "id": self.idObjectif,
            "sportif_id": self.sportifId,
            "exercice_id": self.exerciceId,
            "repetitions_cible": self.repetitionsCible,
            "periode": self.periode,
            "date_limite": self.dateLimite,
            "atteint": self.atteint
        }
