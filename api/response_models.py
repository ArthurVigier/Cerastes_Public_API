"""
Modèles Pydantic standardisés pour les réponses d'API
---------------------------------------------------
Ce module définit les modèles de réponse communs pour assurer la cohérence des API.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

class ErrorResponse(BaseModel):
    """Modèle standard pour les réponses d'erreur"""
    detail: str
    code: Optional[str] = None
    params: Optional[Dict[str, Any]] = None

class SuccessResponse(BaseModel):
    """Modèle pour les réponses de succès simples"""
    success: bool = True
    message: Optional[str] = None

class TaskResponse(BaseModel):
    """Modèle pour la création d'une tâche"""
    task_id: str
    status: str
    message: Optional[str] = None

class TaskStatusResponse(BaseModel):
    """Modèle pour l'état d'une tâche"""
    status: str
    progress: float
    message: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    results: Optional[Dict[str, Any]] = None

class TaskListResponse(BaseModel):
    """Modèle pour la liste des tâches"""
    total: int
    tasks: Dict[str, TaskStatusResponse]

# Modèles spécifiques aux modules
class VideoAnalysisResponse(TaskResponse):
    """Modèle pour les réponses d'analyse vidéo"""
    video_id: str
    analysis_type: str

class TranscriptionResponse(TaskResponse):
    """Modèle pour les réponses de transcription"""
    video_id: str
    transcription_type: str

class VideoExtractionResponse(BaseModel):
    """Response model for video extraction operations"""
    content: str
    file_path: Optional[str] = None
    message: str = "Video extraction successful"

class NonverbalAnalysisResponse(BaseModel):
    """Modèle de réponse pour l'analyse non verbale"""
    analysis: Any  # Contient l'analyse des indices non verbaux
    message: str = "Nonverbal cues analysis successful"