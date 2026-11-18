"""
Repetition - Représente une répétition détectée et mesurée lors d'une séance.
Composition 1-* avec SeanceEntrainement (détruite si la séance est supprimée).
"""
import time


class Repetition:
    def __init__(
        self,
        numero: int,
        horodatage: float = None,
        dureeMs: int = 0,
        amplitude: float = 0.0,
        estCorrecte: bool = True,
        idRepetition: int = None,
        seanceId: int = None
    ):
        self.id = idRepetition
        self.seanceId = seanceId
        self.numero = numero
        self.horodatage = horodatage if horodatage is not None else time.time()
        self.dureeMs = int(dureeMs)
        self.amplitude = float(amplitude)
        self.estCorrecte = bool(estCorrecte)

    def valider(self) -> bool:
        """Vérifie si la répétition satisfait les critères minimaux de validation."""
        return self.estCorrecte and self.dureeMs >= 300 and self.amplitude > 0.0

    def calculerAmplitude(self) -> float:
        """Retourne l'amplitude angulaire (ou métrique) mesurée lors de la répétition."""
        return self.amplitude

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "seance_id": self.seanceId,
            "numero": self.numero,
            "horodatage": self.horodatage,
            "duree_ms": self.dureeMs,
            "amplitude": round(self.amplitude, 1),
            "est_correcte": self.estCorrecte
        }
