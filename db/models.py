from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Float, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from db import Base

class User(Base):
    """Modèle utilisateur pour l'authentification et la gestion des informations de profil."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")

class ApiKey(Base):
    """Modèle pour les clés API."""
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    key = Column(String, unique=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    level = Column(String, default="FREE")  # FREE, PREMIUM, ENTERPRISE
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
    
    # Relations
    user = relationship("User", back_populates="api_keys")
    usage_records = relationship("UsageRecord", back_populates="api_key", cascade="all, delete-orphan")

class UsageRecord(Base):
    """Modèle pour enregistrer l'utilisation des API."""
    __tablename__ = "usage_records"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    api_key_id = Column(String, ForeignKey("api_keys.id"))
    endpoint = Column(String)
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    api_key = relationship("ApiKey", back_populates="usage_records")

# Ajoutez d'autres modèles au besoin
class Task(Base):
    """Modèle pour les tâches asynchrones."""
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String)  # inference, transcription, video_analysis, etc.
    status = Column(String, default="pending")  # pending, running, completed, failed
    progress = Column(Float, default=0.0)
    api_key_id = Column(String, ForeignKey("api_keys.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    results = Column(JSON, nullable=True)
    
    # Relations optionnelles
    api_key = relationship("ApiKey")