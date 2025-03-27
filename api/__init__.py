"""
Package central pour toutes les API REST
---------------------------------------
Ce package initialise et exporte tous les routeurs de l'application.
"""

from fastapi import APIRouter

# Import des routeurs
from .video_router import video_router
from .transcription_router import transcription_router
from .subscription_router import subscription_router
from .auth_router import auth_router
from .health_router import health_router
from .inference_router import inference_router
from .task_router import task_router

# Import des gestionnaires d'erreurs
from . import error_handlers
from . import response_models

# Exporter les modules pour main.py
__all__ = [
    'video_router',
    'transcription_router',
    'subscription_router',
    'auth_router',
    'health_router',
    'inference_router',
    'task_router',
    'error_handlers',
    'response_models'
]