from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional
from datetime import datetime, timedelta
import time

from auth_models import (
    User, UserCreate, UserResponse, ApiKey, ApiKeyCreate, 
    ApiKeyResponse, Token, ApiKeyLevel
)
from auth import (
    authenticate_user, create_access_token, get_current_active_user,
    check_admin_role, get_password_hash, generate_api_key
)
from database import (
    create_user, create_api_key, get_api_keys_for_user,
    update_api_key, delete_api_key, get_user_usage_stats
)

# Configuration des routes
router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={401: {"description": "Non autorisé"}},
)

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Obtient un token JWT en s'authentifiant avec nom d'utilisateur et mot de passe."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.id, "name": user.full_name, "email": user.email, 
              "roles": user.roles, "api_level": user.subscription},
        expires_delta=access_token_expires
    )
    
    # Calculer le timestamp d'expiration
    expires_at = int(time.time()) + int(access_token_expires.total_seconds())
    
    # Créer la réponse utilisateur sans données sensibles
    user_response = UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        roles=user.roles,
        created_at=user.created_at,
        subscription=user.subscription
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_at=expires_at,
        user=user_response
    )

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate):
    """Inscrit un nouvel utilisateur."""
    # Vérifier si l'utilisateur existe déjà
    from database import get_user_by_username
    if get_user_by_username(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un utilisateur avec ce nom d'utilisateur existe déjà"
        )
    
    # Créer l'utilisateur
    hashed_password = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        roles=["user"],
        subscription=ApiKeyLevel.FREE
    )
    
    created_user = create_user(user)
    
    # Retourner la réponse sans données sensibles
    return UserResponse(
        id=created_user.id,
        username=created_user.username,
        email=created_user.email,
        full_name=created_user.full_name,
        roles=created_user.roles,
        created_at=created_user.created_at,
        subscription=created_user.subscription
    )

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Récupère les informations de l'utilisateur actuel."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        roles=current_user.roles,
        created_at=current_user.created_at,
        subscription=current_user.subscription
    )

@router.post("/api-keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key_for_user(
    key_data: ApiKeyCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Crée une nouvelle clé API pour l'utilisateur."""
    # Si un niveau est spécifié et que l'utilisateur n'est pas admin, utiliser le niveau d'abonnement
    if key_data.level and "admin" not in current_user.roles:
        key_data.level = current_user.subscription
    
    # Si aucun niveau n'est spécifié, utiliser le niveau d'abonnement
    level = key_data.level or current_user.subscription
    
    # Générer une nouvelle clé API
    key = generate_api_key()
    
    # Créer l'objet ApiKey
    api_key = ApiKey(
        key=key,
        name=key_data.name,
        user_id=current_user.id,
        level=level,
        expires_at=key_data.expires_at
    )
    
    # Sauvegarder la clé API
    created_key = create_api_key(api_key)
    
    return ApiKeyResponse(
        id=created_key.id,
        key=created_key.key,
        name=created_key.name,
        level=created_key.level,
        created_at=created_key.created_at,
        expires_at=created_key.expires_at,
        is_active=created_key.is_active
    )

@router.get("/api-keys", response_model=List[ApiKeyResponse])
async def get_user_api_keys(current_user: User = Depends(get_current_active_user)):
    """Récupère toutes les clés API de l'utilisateur."""
    api_keys = get_api_keys_for_user(current_user.id)
    
    return [
        ApiKeyResponse(
            id=key.id,
            key=key.key,
            name=key.name,
            level=key.level,
            created_at=key.created_at,
            expires_at=key.expires_at,
            is_active=key.is_active
        )
        for key in api_keys
    ]

@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Supprime une clé API de l'utilisateur."""
    # Vérifier si la clé appartient à l'utilisateur
    api_keys = get_api_keys_for_user(current_user.id)
    key_to_delete = next((key for key in api_keys if key.id == key_id), None)
    
    if not key_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clé API non trouvée"
        )
    
    # Supprimer la clé
    delete_api_key(key_to_delete.key)

@router.put("/api-keys/{key_id}/deactivate", response_model=ApiKeyResponse)
async def deactivate_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Désactive une clé API."""
    # Vérifier si la clé appartient à l'utilisateur
    api_keys = get_api_keys_for_user(current_user.id)
    key_to_update = next((key for key in api_keys if key.id == key_id), None)
    
    if not key_to_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clé API non trouvée"
        )
    
    # Désactiver la clé
    key_to_update.is_active = False
    updated_key = update_api_key(key_to_update)
    
    return ApiKeyResponse(
        id=updated_key.id,
        key=updated_key.key,
        name=updated_key.name,
        level=updated_key.level,
        created_at=updated_key.created_at,
        expires_at=updated_key.expires_at,
        is_active=updated_key.is_active
    )

@router.put("/api-keys/{key_id}/activate", response_model=ApiKeyResponse)
async def activate_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Active une clé API."""
    # Vérifier si la clé appartient à l'utilisateur
    api_keys = get_api_keys_for_user(current_user.id)
    key_to_update = next((key for key in api_keys if key.id == key_id), None)
    
    if not key_to_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clé API non trouvée"
        )
    
    # Activer la clé
    key_to_update.is_active = True
    updated_key = update_api_key(key_to_update)
    
    return ApiKeyResponse(
        id=updated_key.id,
        key=updated_key.key,
        name=updated_key.name,
        level=updated_key.level,
        created_at=updated_key.created_at,
        expires_at=updated_key.expires_at,
        is_active=updated_key.is_active
    )

@router.get("/usage-stats")
async def get_usage_statistics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Récupère les statistiques d'utilisation de l'utilisateur."""
    stats = get_user_usage_stats(current_user.id, start_date, end_date)
    return stats

# Routes d'administration (réservées aux administrateurs)
@router.get("/admin/users", response_model=List[UserResponse])
async def get_all_users(current_user: User = Depends(check_admin_role)):
    """Récupère tous les utilisateurs (admin seulement)."""
    from database import users_db
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            roles=user.roles,
            created_at=user.created_at,
            subscription=user.subscription
        )
        for user in users_db.values()
    ]

@router.put("/admin/users/{user_id}/subscription", response_model=UserResponse)
async def update_user_subscription(
    user_id: str,
    level: ApiKeyLevel = Body(...),
    current_user: User = Depends(check_admin_role)
):
    """Met à jour le niveau d'abonnement d'un utilisateur (admin seulement)."""
    from database import users_db
    
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    # Mettre à jour l'abonnement
    user = users_db[user_id]
    user.subscription = level
    users_db[user_id] = user
    
    # Sauvegarder les modifications
    from database import _save_data
    _save_data()
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        roles=user.roles,
        created_at=user.created_at,
        subscription=user.subscription
    )