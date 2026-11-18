"""
Posture - Ensemble des 33 points clés détectés sur une image caméra avec horodatage et score de confiance.
Formule de calcul d'angle articulaire :
θ = arccos[(BA · BC) / (|BA| × |BC|)]
"""
import math
import time
from typing import List, Dict, Union
from domain.point_cle import PointCle


class Posture:
    # 33 noms standards selon la nomenclature MediaPipe Pose
    NOMS_POINTS_33 = [
        "nose", "left_eye_inner", "left_eye", "left_eye_outer",
        "right_eye_inner", "right_eye", "right_eye_outer",
        "left_ear", "right_ear", "mouth_left", "mouth_right",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_pinky", "right_pinky",
        "left_index", "right_index", "left_thumb", "right_thumb",
        "left_hip", "right_hip", "left_knee", "right_knee",
        "left_ankle", "right_ankle", "left_heel", "right_heel",
        "left_foot_index", "right_foot_index"
    ]

    def __init__(self, pointsCles: List[PointCle], horodatage: float = None, confiance: float = 1.0):
        self.horodatage = horodatage if horodatage is not None else time.time()
        self.confiance = float(confiance)
        self.pointsCles: List[PointCle] = pointsCles
        self._map_points: Dict[str, PointCle] = {p.nom: p for p in pointsCles}

    def getPoint(self, identifiant: Union[str, int]) -> PointCle:
        if isinstance(identifiant, int):
            if 0 <= identifiant < len(self.pointsCles):
                return self.pointsCles[identifiant]
            raise IndexError(f"Index de point {identifiant} invalide.")
        if identifiant in self._map_points:
            return self._map_points[identifiant]
        raise KeyError(f"Point clé '{identifiant}' non trouvé dans la posture.")

    def getAngle(self, a: Union[str, int, PointCle], b: Union[str, int, PointCle], c: Union[str, int, PointCle]) -> float:
        """
        Calcule l'angle à l'articulation B formée par les trois points A, B, C.
        BA = A - B, BC = C - B
        θ = arccos[(BA · BC) / (|BA| × |BC|)]
        Renvoie l'angle en degrés (0 à 180°).
        """
        ptA = a if isinstance(a, PointCle) else self.getPoint(a)
        ptB = b if isinstance(b, PointCle) else self.getPoint(b)
        ptC = c if isinstance(c, PointCle) else self.getPoint(c)

        # Vecteur BA = A - B
        ba_x = ptA.x - ptB.x
        ba_y = ptA.y - ptB.y
        ba_z = ptA.z - ptB.z

        # Vecteur BC = C - B
        bc_x = ptC.x - ptB.x
        bc_y = ptC.y - ptB.y
        bc_z = ptC.z - ptB.z

        # Produit scalaire BA · BC
        produit_scalaire = ba_x * bc_x + ba_y * bc_y + ba_z * bc_z

        # Normes |BA| et |BC|
        norme_ba = math.sqrt(ba_x * ba_x + ba_y * ba_y + ba_z * ba_z)
        norme_bc = math.sqrt(bc_x * bc_x + bc_y * bc_y + bc_z * bc_z)

        if norme_ba * norme_bc == 0:
            return 0.0

        cos_theta = produit_scalaire / (norme_ba * norme_bc)
        # Écrêtage pour éviter les erreurs d'arrondi hors [-1, 1]
        cos_theta = max(-1.0, min(1.0, cos_theta))
        angle_rad = math.acos(cos_theta)
        return math.degrees(angle_rad)

    def estComplete(self, seuil_confiance: float = 0.5) -> bool:
        """Vérifie si la posture contient au moins les 33 points et une visibilité suffisante."""
        if len(self.pointsCles) < 33:
            return False
        if self.confiance < seuil_confiance:
            return False
        # Au moins les points articulaires principaux doivent être visibles
        principaux = ["left_shoulder", "right_shoulder", "left_hip", "right_hip"]
        for nom in principaux:
            if nom in self._map_points and self._map_points[nom].visibilite < 0.3:
                return False
        return True

    def to_dict(self) -> dict:
        return {
            "horodatage": self.horodatage,
            "confiance": self.confiance,
            "pointsCles": [p.to_dict() for p in self.pointsCles]
        }
