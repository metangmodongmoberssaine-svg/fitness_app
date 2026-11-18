"""
Router Administration.
Cas d'utilisation : Gérer les utilisateurs (Admin), Consulter les statistiques globales (Admin).
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database.repository import AdminRepository

router = APIRouter(prefix="/api/admin", tags=["Administration"])


class RoleUpdateRequest(BaseModel):
    role: str
    niveau_acces: int = 1


@router.get("/users")
def get_users():
    """Gérer les utilisateurs : liste tous les comptes inscrits."""
    return AdminRepository.get_all_users()


@router.put("/users/{user_id}/role")
def update_user_role(user_id: int, req: RoleUpdateRequest):
    """Modifier les droits et rôles d'un utilisateur."""
    AdminRepository.update_role(user_id, req.role, req.niveau_acces)
    return {"message": "Rôle mis à jour avec succès"}


@router.get("/statistiques")
def get_statistics():
    """Consulter le tableau de bord et les statistiques globales de la plateforme."""
    return AdminRepository.get_global_statistics()
