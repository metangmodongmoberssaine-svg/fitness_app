"""
Notification - Message envoyé au sportif (ex: atteinte d'un objectif, félicitations).
Association 1-* avec Sportif.
Simule ou interagit avec le Service de notification (Acteur secondaire externe).
"""
from datetime import datetime
from typing import Optional


class Notification:
    def __init__(
        self,
        sportifId: int,
        message: str,
        canal: str = "push",
        dateEnvoi: Optional[str] = None,
        idNotification: Optional[int] = None
    ):
        self.idNotification = idNotification
        self.sportifId = int(sportifId)
        self.message = message
        self.canal = canal  # 'push', 'in_app', 'email'
        self.dateEnvoi = dateEnvoi or datetime.now().isoformat()
        self.statut = "envoyee"

    def envoyer(self) -> bool:
        """
        Transmet la notification au sportif via le canal spécifié (Service externe).
        Dans cette implémentation, valide l'envoi et consigne l'événement.
        """
        print(f"[ServiceNotification externe] Canal={self.canal} -> Sportif={self.sportifId} : {self.message}")
        self.statut = "livree"
        return True

    def to_dict(self) -> dict:
        return {
            "id": self.idNotification,
            "sportif_id": self.sportifId,
            "message": self.message,
            "canal": self.canal,
            "date_envoi": self.dateEnvoi,
            "statut": self.statut
        }
