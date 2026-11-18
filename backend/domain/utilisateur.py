"""
Utilisateur, Sportif, Administrateur - Modèle d'utilisateurs et héritage.
Utilisateur : classe abstraite factorisant les attributs et méthodes communes.
Sportif : hérite de Utilisateur (acteur principal qui s'entraîne).
Administrateur : hérite de Utilisateur (acteur principal qui gère catalogue, règles, utilisateurs, stats).
Héritage persistant en table unique avec colonne discriminator 'role'.
"""
from abc import ABC
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from domain.exercice import Exercice
from domain.regle_de_comptage import RegleDeComptage
from domain.seance_entrainement import SeanceEntrainement
from domain.objectif import Objectif


class Utilisateur(ABC):
    def __init__(
        self,
        nom: str,
        prenom: str,
        email: str,
        motDePasse: str,
        role: str,
        idUtilisateur: Optional[int] = None,
        dateInscription: Optional[str] = None
    ):
        self.idUtilisateur = idUtilisateur
        self.nom = nom
        self.prenom = prenom
        self.email = email.lower().strip()
        self.motDePasse = motDePasse  # Haché SHA-256
        self.role = role
        self.dateInscription = dateInscription or datetime.now().isoformat()
        self.estConnecte = False

    @staticmethod
    def hacherMotDePasse(mdpClair: str) -> str:
        return hashlib.sha256(mdpClair.encode("utf-8")).hexdigest()

    def sAuthentifier(self, motDePasseClair: str) -> bool:
        """Vérifie le mot de passe fourni avec le hachage sécurisé enregistré."""
        hash_fourni = self.hacherMotDePasse(motDePasseClair)
        if hash_fourni == self.motDePasse:
            self.estConnecte = True
            return True
        return False

    def seDeconnecter(self) -> None:
        """Déconnecte la session utilisateur."""
        self.estConnecte = False

    def modifierProfil(self, nom: Optional[str] = None, prenom: Optional[str] = None, email: Optional[str] = None, **kwargs) -> None:
        """Met à jour les informations de profil."""
        if nom:
            self.nom = nom
        if prenom:
            self.prenom = prenom
        if email:
            self.email = email.lower().strip()

    def to_dict(self) -> dict:
        return {
            "id": self.idUtilisateur,
            "nom": self.nom,
            "prenom": self.prenom,
            "email": self.email,
            "role": self.role,
            "date_inscription": self.dateInscription
        }


class Sportif(Utilisateur):
    def __init__(
        self,
        nom: str,
        prenom: str,
        email: str,
        motDePasse: str,
        poids: float = 70.0,
        taille: float = 175.0,
        niveau: str = "Intermédiaire",
        idUtilisateur: Optional[int] = None,
        dateInscription: Optional[str] = None
    ):
        super().__init__(nom, prenom, email, motDePasse, role="sportif", idUtilisateur=idUtilisateur, dateInscription=dateInscription)
        self.poids = float(poids)
        self.taille = float(taille)
        self.niveau = niveau

    def lancerSeance(self, e: Exercice) -> SeanceEntrainement:
        """Instancie une nouvelle séance d'entraînement liée à un exercice."""
        seance = SeanceEntrainement(
            sportifId=self.idUtilisateur or 0,
            exerciceId=e.idExercice or 0
        )
        return seance

    def definirObjectif(self, o: Objectif) -> None:
        """Attribue un objectif personnel au sportif."""
        o.sportifId = self.idUtilisateur or 0

    def consulterHistorique(self) -> List[dict]:
        """Méthode métier pour l'accès aux séances (relayé par le repository)."""
        return []

    def consulterProgression(self) -> Dict[str, Any]:
        """Méthode métier pour synthétiser les progrès (relayé par le repository)."""
        return {}

    def modifierProfil(self, nom=None, prenom=None, email=None, poids=None, taille=None, niveau=None, **kwargs) -> None:
        super().modifierProfil(nom, prenom, email, **kwargs)
        if poids is not None:
            self.poids = float(poids)
        if taille is not None:
            self.taille = float(taille)
        if niveau is not None:
            self.niveau = niveau

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "poids": self.poids,
            "taille": self.taille,
            "niveau": self.niveau
        })
        return d


class Administrateur(Utilisateur):
    def __init__(
        self,
        nom: str,
        prenom: str,
        email: str,
        motDePasse: str,
        niveauAcces: int = 1,
        idUtilisateur: Optional[int] = None,
        dateInscription: Optional[str] = None
    ):
        super().__init__(nom, prenom, email, motDePasse, role="administrateur", idUtilisateur=idUtilisateur, dateInscription=dateInscription)
        self.niveauAcces = int(niveauAcces)

    def gererCatalogue(self) -> List[dict]:
        """Méthode métier d'administration du catalogue."""
        return []

    def parametrerRegles(self, r: RegleDeComptage) -> None:
        """Configure et ajuste les seuils angulaires d'une règle."""
        pass

    def gererUtilisateurs(self) -> List[dict]:
        """Méthode métier de consultation et administration des comptes."""
        return []

    def consulterStatistiques(self) -> Dict[str, Any]:
        """Méthode métier pour le rapport de statistiques globales."""
        return {}

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "niveau_acces": self.niveauAcces
        })
        return d
