"""
RetourCorrection - Conseil émis en temps réel lors d'une posture incorrecte.
Composition 1-* avec SeanceEntrainement (rattaché à la séance où il a été émis).
"""
import time


class RetourCorrection:
    def __init__(
        self,
        message: str,
        typeRetour: str = "mixte",
        gravite: int = 1,
        idRetour: int = None,
        seanceId: int = None,
        horodatage: float = None
    ):
        self.idRetour = idRetour
        self.seanceId = seanceId
        self.message = message
        self.type = typeRetour  # 'visuel', 'sonore', ou 'mixte'
        self.gravite = int(gravite)  # 1 = conseil léger, 2 = avertissement, 3 = risque de blessure
        self.horodatage = horodatage if horodatage is not None else time.time()

    def afficher(self) -> dict:
        """Formate le message et son niveau pour affichage visuel sur l'interface."""
        return {
            "id": self.idRetour,
            "message": self.message,
            "gravite": self.gravite,
            "type": self.type,
            "horodatage": self.horodatage
        }

    def emettreSon(self) -> str:
        """Génère le texte ou le signal à prononcer / jouer pour le retour sonore."""
        return self.message

    def to_dict(self) -> dict:
        return {
            "id": self.idRetour,
            "seance_id": self.seanceId,
            "message": self.message,
            "type": self.type,
            "gravite": self.gravite,
            "horodatage": self.horodatage
        }
