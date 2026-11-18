"""
CompteurRepetitions - Machine à états gérant le décompte des répétitions par hystérésis et contrôle de posture.
Responsabilité Unique (SRP) : le compteur gère l'état de l'exercice et se teste sans caméra.
Dépendance vers Posture : traiter(p) reçoit une posture en paramètre sans la conserver.
"""
import time
from typing import Optional, Tuple, List
from domain.posture import Posture
from domain.regle_de_comptage import RegleDeComptage
from domain.repetition import Repetition
from domain.retour_correction import RetourCorrection


class CompteurRepetitions:
    def __init__(self, regle: RegleDeComptage):
        self.regle = regle
        self.total = 0
        self.phaseCourante = "haute"  # Initialement en position haute (départ)
        self.derniereTransition = time.time()
        self.tempsDebutRepetition = time.time()
        self.angleMinObserve = 999.0
        self.angleMaxObserve = 0.0
        self.historiqueRepetitions: List[Repetition] = []
        self.historiqueCorrections: List[RetourCorrection] = []

    def reinitialiser(self) -> None:
        """Réinitialise les compteurs et l'état de la machine."""
        self.total = 0
        self.phaseCourante = "haute"
        self.derniereTransition = time.time()
        self.tempsDebutRepetition = time.time()
        self.angleMinObserve = 999.0
        self.angleMaxObserve = 0.0
        self.historiqueRepetitions.clear()
        self.historiqueCorrections.clear()

    def incrementer(self) -> None:
        """Incrémente directement le compteur de répétitions."""
        self.total += 1

    def getTotal(self) -> int:
        """Retourne le nombre total de répétitions validées."""
        return self.total

    def extraireValeurArticulation(self, p: Posture) -> float:
        """Extrait l'angle ou la métrique selon l'articulation suivie dans la règle."""
        art = self.regle.articulationCle.lower()

        if "genou" in art or "squat" in art:
            # Angle Hanche - Genou - Cheville (gauche ou droite)
            try:
                angle_gauche = p.getAngle("left_hip", "left_knee", "left_ankle")
                return angle_gauche
            except Exception:
                return p.getAngle("right_hip", "right_knee", "right_ankle")

        elif "coude" in art or "pompe" in art or "traction" in art or "biceps" in art:
            # Angle Épaule - Coude - Poignet
            try:
                angle_g = p.getAngle("left_shoulder", "left_elbow", "left_wrist")
                angle_d = p.getAngle("right_shoulder", "right_elbow", "right_wrist")
                return (angle_g + angle_d) / 2.0
            except Exception:
                return p.getAngle("left_shoulder", "left_elbow", "left_wrist")

        elif "distance" in art or "poignet" in art or "chest" in art:
            # Distance horizontale entre les deux poignets
            w_left = p.getPoint("left_wrist")
            w_right = p.getPoint("right_wrist")
            return abs(w_left.x - w_right.x)

        elif "hanche" in art:
            return p.getAngle("left_shoulder", "left_hip", "left_knee")

        else:
            # Par défaut, angle coude gauche
            return p.getAngle("left_shoulder", "left_elbow", "left_wrist")

    def traiter(self, p: Posture) -> Tuple[bool, Optional[RetourCorrection], Optional[Repetition], float]:
        """
        Traite une posture ponctuelle.
        Machine à états :
        1. Passe de 'haute' à 'basse' dès franchissement du seuil bas (avec tolérance).
        2. Revient de 'basse' à 'haute' dès franchissement du seuil haut.
        3. Valide la répétition si durée >= dureeMinRepetition et amplitude suffisante.
        Retourne : (repetition_validee: bool, correction: Optional[RetourCorrection], repetition: Optional[Repetition], valeur_mesuree: float)
        """
        valeur = self.extraireValeurArticulation(p)
        maintenant = time.time()

        # Suivi des extrêmes pour calculer l'amplitude réelle de la répétition
        if valeur < self.angleMinObserve:
            self.angleMinObserve = valeur
        if valeur > self.angleMaxObserve:
            self.angleMaxObserve = valeur

        repetition_validee = False
        repetition_creee = None
        correction_emise = None

        # Contrôle posture via la règle
        conseil = self.regle.evaluerPosture(valeur)
        if conseil:
            correction_emise = RetourCorrection(
                message=conseil["message"],
                typeRetour=conseil.get("type", "mixte"),
                gravite=conseil.get("gravite", 1),
                horodatage=maintenant
            )
            # Éviter le spam de corrections identiques trop rapprochées (< 2 secondes)
            if not self.historiqueCorrections or (maintenant - self.historiqueCorrections[-1].horodatage > 2.0):
                self.historiqueCorrections.append(correction_emise)
            else:
                correction_emise = None

        phase_evaluee = self.regle.evaluerPhase(valeur)

        if self.phaseCourante == "haute":
            if phase_evaluee == "basse":
                # Transition vers phase basse
                self.phaseCourante = "basse"
                self.derniereTransition = maintenant
                self.tempsDebutRepetition = maintenant

        elif self.phaseCourante == "basse":
            if phase_evaluee == "haute":
                # Retour en position haute : cycle complet haut-bas-haut !
                duree_ms = int((maintenant - self.tempsDebutRepetition) * 1000)
                amplitude = abs(self.angleMaxObserve - self.angleMinObserve)

                nouvelle_rep = Repetition(
                    numero=self.total + 1,
                    horodatage=maintenant,
                    dureeMs=duree_ms,
                    amplitude=amplitude,
                    estCorrecte=(duree_ms >= self.regle.dureeMinRepetition)
                )

                if self.regle.estRepetitionValide(nouvelle_rep):
                    self.incrementer()
                    repetition_validee = True
                    self.historiqueRepetitions.append(nouvelle_rep)
                    repetition_creee = nouvelle_rep

                # Réinitialiser pour la prochaine répétition
                self.phaseCourante = "haute"
                self.derniereTransition = maintenant
                self.angleMinObserve = 999.0
                self.angleMaxObserve = 0.0

        return repetition_validee, correction_emise, repetition_creee, valeur
