"""
Exercice - Représente un mouvement du catalogue (ex: Squat, Pompe, Traction, Dumbbell curl, Chest fly).
Composition 1-1 avec RegleDeComptage (la règle disparaît avec l'exercice).
"""
from typing import Optional
from domain.regle_de_comptage import RegleDeComptage


class Exercice:
    def __init__(
        self,
        nom: str,
        description: str,
        groupeMusculaire: str,
        difficulte: int = 1,
        idExercice: Optional[int] = None,
        regle: Optional[RegleDeComptage] = None
    ):
        self.idExercice = idExercice
        self.nom = nom
        self.description = description
        self.groupeMusculaire = groupeMusculaire
        self.difficulte = int(difficulte)
        self.regle = regle

    def getDetails(self) -> str:
        """Retourne un descriptif complet de l'exercice pour le sportif ou l'affichage."""
        diff_labels = {1: "Débutant", 2: "Intermédiaire", 3: "Avancé"}
        diff_str = diff_labels.get(self.difficulte, "Tous niveaux")
        regle_info = f", Suivi: {self.regle.articulationCle}" if self.regle else ""
        return f"{self.nom} ({self.groupeMusculaire}) - Niveau: {diff_str}{regle_info}. {self.description}"

    def getRegle(self) -> Optional[RegleDeComptage]:
        """Retourne la règle de comptage associée."""
        return self.regle

    def to_dict(self) -> dict:
        return {
            "id": self.idExercice,
            "nom": self.nom,
            "description": self.description,
            "groupe_musculaire": self.groupeMusculaire,
            "difficulte": self.difficulte,
            "regle": self.regle.to_dict() if self.regle else None
        }
