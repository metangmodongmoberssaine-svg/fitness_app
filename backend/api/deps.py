"""
Dépendances d'authentification partagées par les routes protégées.

Le jeton est celui renvoyé par /api/auth/login : "token-<id>-<role>".
Le serveur NE FAIT PAS confiance au rôle écrit dans le jeton : il relit
l'utilisateur dans la base et compare.
"""
from typing import Optional
from fastapi import Header, HTTPException, Depends
from database.repository import AuthRepository


def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Connexion requise.")
    token = authorization.split(" ", 1)[1].strip()
    parts = token.split("-")
    if len(parts) != 3 or parts[0] != "token" or not parts[1].isdigit():
        raise HTTPException(status_code=401, detail="Jeton invalide.")
    user = AuthRepository.get_by_id(int(parts[1]))
    if not user or user.role != parts[2]:
        raise HTTPException(status_code=401, detail="Session invalide, reconnectez-vous.")
    return user


def require_admin(user=Depends(get_current_user)):
    if user.role != "administrateur":
        raise HTTPException(status_code=403, detail="Action réservée à l'administrateur.")
    return user