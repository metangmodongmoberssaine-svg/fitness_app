"""
RegleDeComptage - Décrit comment détecter une répétition (articulation suivie, seuils d'angle, hystérésis, tolérance).
Conception pilotée par les données (Data-Driven Design) :
Permet d'ajouter ou d'ajuster un exercice sans modifier le code de l'application.
Composition 1-1 avec Exercice.
"""
from typing import Optional


class RegleDeComptage:
    def __init__(
        self,
        articulationCle: str,
        angleHaut: float,
        angleBas: float,
        tolerance: float = 10.0,
        dureeMinRepetition: int = 600,
        idRegle: Optional[int] = None,
        exerciceId: Optional[int] = None
    ):
        self.idRegle = idRegle
        self.exerciceId = exerciceId
        self.articulationCle = articulationCle  # ex: 'genou', 'coude', 'distance_poignets'
        self.angleHaut = float(angleHaut)  # Position haute/départ (ex: jambe tendue 160°)
        self.angleBas = float(angleBas)    # Position basse/inflexion (ex: cuisse fléchie 90°)
        self.tolerance = float(tolerance)  # Marge de tolérance angulaire
        self.dureeMinRepetition = int(dureeMinRepetition)  # Durée min en ms pour éviter rebonds/bruits

    def evaluerPhase(self, valeur: float) -> str:
        """
        Évalue la phase du mouvement selon le mécanisme d'hystérésis :
        - 'haute' : articulation en extension / position de repos
        - 'basse' : articulation en flexion / position contractée
        - 'transition' : zone intermédiaire
        """
        # Pour les exercices où l'angle haut > angle bas (squat, pompe, dumbbell curl, traction)
        if self.angleHaut > self.angleBas:
            if valeur >= (self.angleHaut - self.tolerance):
                return "haute"
            elif valeur <= (self.angleBas + self.tolerance):
                return "basse"
            else:
                return "transition"
        else:
            # Cas inversé (si angle bas > angle haut, ex: distance)
            if valeur <= (self.angleHaut + self.tolerance):
                return "haute"
            elif valeur >= (self.angleBas - self.tolerance):
                return "basse"
            else:
                return "transition"

    def estRepetitionValide(self, r: "Repetition") -> bool:
        """Valide qu'une répétition respecte les seuils de durée et d'amplitude fixés par la règle."""
        amplitude_attendue = abs(self.angleHaut - self.angleBas)
        # La répétition doit couvrir au moins 70% de l'amplitude théorique et durer le temps min
        amplitude_suffisante = r.amplitude >= (amplitude_attendue * 0.7)
        duree_suffisante = r.dureeMs >= self.dureeMinRepetition
        return amplitude_suffisante and duree_suffisante

    def evaluerPosture(self, angle: float) -> Optional[dict]:
        """
        Vérifie si la posture est correcte ou si elle dépasse la tolérance admissible.
        Renvoie un conseil de correction le cas échéant.
        """
        if self.angleHaut > self.angleBas:
            # Ex: Squat ou pompe où l'on ne descend pas assez bas
            if angle > (self.angleBas + self.tolerance * 2.5) and angle < self.angleHaut - 10:
                return {
                    "message": "Descendez plus bas pour valider l'amplitude complète !",
                    "gravite": 1,
                    "type": "mixte"
                }
            elif angle < (self.angleBas - 25):
                return {
                    "message": "Attention à l'hyperflexion articulaire, remontez légèrement !",
                    "gravite": 2,
                    "type": "mixte"
                }
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.idRegle,
            "exercice_id": self.exerciceId,
            "articulation_cle": self.articulationCle,
            "angle_haut": self.angleHaut,
            "angle_bas": self.angleBas,
            "tolerance": self.tolerance,
            "duree_min_repetition": self.dureeMinRepetition
        }
