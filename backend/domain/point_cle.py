"""
PointCle - Représente un point clé anatomique du corps humain (ex: genou gauche, épaule droite).
Composition 1-33 avec Posture conformément au diagramme de classes (Figure 2).
"""
import math


class PointCle:
    def __init__(self, nom: str, x: float, y: float, z: float = 0.0, visibilite: float = 1.0):
        self.nom = nom
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self.visibilite = float(visibilite)

    def distanceVers(self, p: "PointCle") -> float:
        """Calcule la distance euclidienne vers un autre point clé."""
        return math.sqrt((self.x - p.x) ** 2 + (self.y - p.y) ** 2 + (self.z - p.z) ** 2)

    def to_dict(self) -> dict:
        return {
            "nom": self.nom,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "visibilite": self.visibilite
        }
