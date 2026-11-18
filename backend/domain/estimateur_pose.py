"""
IEstimateurPose - Interface abstraite pour l'estimation de pose (DIP - Dependency Inversion Principle).
EstimateurMediaPipe - Implémentation concrète basée sur Google MediaPipe Pose.
Motif Stratégie : permet de substituer MediaPipe par YOLOv8-pose, MoveNet ou un mock de test sans modifier le moteur.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
import time
from domain.posture import Posture
from domain.point_cle import PointCle


class IEstimateurPose(ABC):
    @abstractmethod
    def estimer(self, img) -> Optional[Posture]:
        """Estime la pose sur une image donnée et renvoie un objet Posture (33 points) ou None."""
        pass


class EstimateurMediaPipe(IEstimateurPose):
    def __init__(self, modele: str = "MediaPipe Pose Full", min_detection_confidence: float = 0.5, min_tracking_confidence: float = 0.5):
        self.modele = modele
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self._pose = None
        self._mp_pose = None
        self._init_mediapipe()

    def _init_mediapipe(self):
        try:
            import mediapipe as mp
            self._mp_pose = mp.solutions.pose
            self._pose = self._mp_pose.Pose(
                static_image_mode=False,
                min_detection_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_tracking_confidence
            )
        except Exception:
            # Si MediaPipe n'est pas installé dans cet environnement précis, fonctionnement silencieux
            self._pose = None

    def estimer(self, img) -> Optional[Posture]:
        """Traite une image BGR/RGB OpenCV ou tableau d'octets."""
        if self._pose is None:
            return None

        try:
            import cv2
            if len(img.shape) == 3 and img.shape[2] == 3:
                # BGR vers RGB
                rgb_frame = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            else:
                rgb_frame = img

            results = self._pose.process(rgb_frame)
            if not results.pose_landmarks:
                return None

            h, w = img.shape[:2]
            points: List[PointCle] = []
            for i, lm in enumerate(results.pose_landmarks.landmark):
                nom = Posture.NOMS_POINTS_33[i] if i < len(Posture.NOMS_POINTS_33) else f"point_{i}"
                points.append(PointCle(
                    nom=nom,
                    x=lm.x * w,
                    y=lm.y * h,
                    z=lm.z * w,
                    visibilite=lm.visibility if hasattr(lm, "visibility") else 1.0
                ))

            return Posture(pointsCles=points, horodatage=time.time(), confiance=0.9)
        except Exception as e:
            print(f"[EstimateurMediaPipe] Erreur d'estimation: {e}")
            return None


class MockEstimateurPose(IEstimateurPose):
    """Estimateur de test permettant d'injecter des poses synthétiques pour les tests unitaires sans caméra."""
    def __init__(self, posture_a_renvoyer: Optional[Posture] = None):
        self.posture = posture_a_renvoyer

    def setPosture(self, p: Posture):
        self.posture = p

    def estimer(self, img) -> Optional[Posture]:
        return self.posture
