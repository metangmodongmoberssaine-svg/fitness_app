"""
Router Authentification : S'inscrire, S'authentifier, Consulter/Modifier Profil.
Acteurs : Visiteur, Sportif, Administrateur.
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
from database.repository import AuthRepository
from database.db import hash_password

router = APIRouter(prefix="/api/auth", tags=["Authentification"])


class RegisterRequest(BaseModel):
    nom: str
    prenom: str
    email: str
    mot_de_passe: str
    role: str = "sportif"
    poids: float = 70.0
    taille: float = 175.0
    niveau: str = "Intermédiaire"


class LoginRequest(BaseModel):
    email: str
    mot_de_passe: str


class ProfileUpdateRequest(BaseModel):
    user_id: int
    nom: str
    prenom: str
    email: str
    poids: float
    taille: float
    niveau: str


@router.post("/register")
def register(req: RegisterRequest):
    existing = AuthRepository.get_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="Un compte existe déjà avec cette adresse email.")
    
    user = AuthRepository.create_user(
        nom=req.nom,
        prenom=req.prenom,
        email=req.email,
        mot_de_passe_clair=req.mot_de_passe,
        role=req.role,
        poids=req.poids,
        taille=req.taille,
        niveau=req.niveau
    )
    return {
        "message": "Inscription réussie",
        "user": user.to_dict()
    }


@router.post("/login")
def login(req: LoginRequest):
    user = AuthRepository.get_by_email(req.email)
    if not user:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")
    
    if not user.sAuthentifier(req.mot_de_passe):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")
    
    # Pour un environnement de développement simple et réactif, on utilise l'ID utilisateur comme jeton
    return {
        "message": "Authentification réussie",
        "token": f"token-{user.idUtilisateur}-{user.role}",
        "user": user.to_dict()
    }


@router.get("/profile/{user_id}")
def get_profile(user_id: int):
    user = AuthRepository.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")
    return user.to_dict()


@router.put("/profile")
def update_profile(req: ProfileUpdateRequest):
    success = AuthRepository.update_profile(
        user_id=req.user_id,
        nom=req.nom,
        prenom=req.prenom,
        email=req.email,
        poids=req.poids,
        taille=req.taille,
        niveau=req.niveau
    )
    user = AuthRepository.get_by_id(req.user_id)
    return {
        "message": "Profil mis à jour avec succès",
        "user": user.to_dict() if user else None
    }
