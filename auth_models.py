from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

class ApiKeyLevel(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class UsageLimit(BaseModel):
    """Limites d'utilisation pour différents niveaux d'API"""
    daily_requests: int = Field(..., description="Nombre maximum de requêtes par jour")
    monthly_requests: int = Field(..., description="Nombre maximum de requêtes par mois")
    max_tokens_per_request: int = Field(..., description="Nombre maximum de tokens par requête")
    max_text_length: int = Field(..., description="Longueur maximale du texte en caractères")
    batch_processing: bool = Field(..., description="Accès au traitement par lots")
    max_concurrent_requests: int = Field(..., description="Nombre maximum de requêtes simultanées")
    advanced_models: bool = Field(..., description="Accès aux modèles avancés")

class ApiKey(BaseModel):
    """Modèle pour les clés API"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="ID unique de la clé API")
    key: str = Field(..., description="Clé API (hachée dans la base de données)")
    name: str = Field(..., description="Nom descriptif de la clé")
    user_id: str = Field(..., description="ID de l'utilisateur propriétaire")
    level: ApiKeyLevel = Field(default=ApiKeyLevel.FREE, description="Niveau d'accès")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Date de création")
    last_used_at: Optional[datetime] = Field(None, description="Dernière utilisation")
    expires_at: Optional[datetime] = Field(None, description="Date d'expiration")
    is_active: bool = Field(default=True, description="Si la clé est active")
    usage: Dict[str, int] = Field(default_factory=dict, description="Statistiques d'utilisation")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TokenData(BaseModel):
    """Données contenues dans le token JWT"""
    sub: str = Field(..., description="ID de l'utilisateur")
    name: Optional[str] = Field(None, description="Nom de l'utilisateur")
    email: Optional[str] = Field(None, description="Email de l'utilisateur")
    roles: List[str] = Field(default_factory=list, description="Rôles de l'utilisateur")
    api_level: ApiKeyLevel = Field(default=ApiKeyLevel.FREE, description="Niveau d'API")
    exp: Optional[int] = Field(None, description="Expiration du token (timestamp)")

class User(BaseModel):
    """Modèle pour les utilisateurs"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="ID unique de l'utilisateur")
    username: str = Field(..., description="Nom d'utilisateur")
    email: EmailStr = Field(..., description="Email de l'utilisateur")
    hashed_password: str = Field(..., description="Mot de passe haché")
    full_name: Optional[str] = Field(None, description="Nom complet")
    disabled: bool = Field(default=False, description="Si le compte est désactivé")
    roles: List[str] = Field(default_factory=lambda: ["user"], description="Rôles de l'utilisateur")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Date de création")
    subscription: ApiKeyLevel = Field(default=ApiKeyLevel.FREE, description="Niveau d'abonnement")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserCreate(BaseModel):
    """Modèle pour la création d'utilisateurs"""
    username: str = Field(..., description="Nom d'utilisateur", min_length=3, max_length=50)
    email: EmailStr = Field(..., description="Email de l'utilisateur")
    password: str = Field(..., description="Mot de passe", min_length=8)
    full_name: Optional[str] = Field(None, description="Nom complet")
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('Le nom d\'utilisateur doit être alphanumérique')
        return v

class UserResponse(BaseModel):
    """Modèle pour la réponse utilisateur (sans données sensibles)"""
    id: str
    username: str
    email: EmailStr
    full_name: Optional[str]
    roles: List[str]
    created_at: datetime
    subscription: ApiKeyLevel
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Token(BaseModel):
    """Modèle pour le token d'authentification"""
    access_token: str
    token_type: str = "bearer"
    expires_at: int
    user: UserResponse

class ApiKeyCreate(BaseModel):
    """Modèle pour la création d'une clé API"""
    name: str = Field(..., description="Nom descriptif de la clé", min_length=3, max_length=50)
    level: Optional[ApiKeyLevel] = Field(None, description="Niveau d'accès (admin only)")
    expires_at: Optional[datetime] = Field(None, description="Date d'expiration (optionnel)")

class ApiKeyResponse(BaseModel):
    """Modèle pour la réponse de clé API"""
    id: str
    key: str
    name: str
    level: ApiKeyLevel
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UsageRecord(BaseModel):
    """Modèle pour l'enregistrement d'utilisation"""
    user_id: str
    api_key_id: str
    request_path: str
    request_method: str
    tokens_input: int = 0
    tokens_output: int = 0
    processing_time: float
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }