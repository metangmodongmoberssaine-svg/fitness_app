"""
MoteurVision - Orchestre l'analyse des images et délègue le comptage au CompteurRepetitions.
Dépendance vers l'interface IEstimateurPose (jamais directement d'une technologie précise).
Conserve la dernière posture (Association 1 -> 0..1).
"""
from typing import Optional, Dict, Any
from domain.estimateur_pose import IEstimateurPose, EstimateurMediaPipe
from domain.posture import Posture
from domain.regle_de_comptage import RegleDeComptage
from domain.compteur_repetitions import CompteurRepetitions


class MoteurVision:
    def __init__(
        self,
        estimateur: Optional[IEstimateurPose] = None,
        resolutionCamera: str = "1280x720",
        imagesParSeconde: int = 30,
        seuilConfiance: float = 0.5
    ):
        self.resolutionCamera = resolutionCamera
        self.imagesParSeconde = imagesParSeconde
        self.seuilConfiance = float(seuilConfiance)
        self.estimateur: IEstimateurPose = estimateur or EstimateurMediaPipe()
        self.dernierePosture: Optional[Posture] = None
        self.compteur: Optional[CompteurRepetitions] = None
        self.suspendu: bool = False

    def initialiser(self, regle: RegleDeComptage) -> None:
        """Initialise le moteur avec la règle de comptage de l'exercice choisi."""
        self.compteur = CompteurRepetitions(regle)
        self.dernierePosture = None
        self.suspendu = False

    def analyserImage(self, img) -> Optional[Posture]:
        """Estime la posture (33 points) via l'estimateur de pose."""
        if self.suspendu:
            return None
        posture = self.estimateur.estimer(img)
        if posture and posture.confiance >= self.seuilConfiance:
            self.dernierePosture = posture
            return posture
        return None

    def traiterPosture(self, p: Posture) -> Dict[str, Any]:
        """
        Calcule les angles et transmet la posture au compteur (machine à états).
        Retourne le résultat de l'analyse pour la trame courante.
        """
        if self.suspendu or self.compteur is None:
            return {"active": False, "total": 0, "rep_validee": False}

        rep_validee, correction, nouvelle_rep, angle = self.compteur.traiter(p)

        return {
            "active": True,
            "angle": round(angle, 1),
            "phase": self.compteur.phaseCourante,
            "total": self.compteur.getTotal(),
            "rep_validee": rep_validee,
            "repetition": nouvelle_rep.to_dict() if nouvelle_rep else None,
            "correction": correction.to_dict() if correction else None
        }

    def suspendre(self) -> None:
        """Suspend l'analyse (mise en pause de la séance)."""
        self.suspendu = True

    def reprendre(self) -> None:
        """Reprend l'analyse."""
        self.suspendu = False

    def getCompteur(self) -> Optional[CompteurRepetitions]:
        return self.compteur
