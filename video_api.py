from fastapi import APIRouter, File, UploadFile, BackgroundTasks, HTTPException, Depends, Form, Request, Query
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Union, Any
import os
import uuid
import time
import json
import aiofiles
import logging
import asyncio
from tempfile import NamedTemporaryFile
from pathlib import Path

# Par:
from video_models import extract_video_content, analyze_manipulation_strategies, extract_nonverbal, analyze_nonverbal

# Import des dépendances d'authentification
from auth import validate_api_key, authorize_advanced_models
from database import record_api_usage
from auth_models import UsageRecord

# Configuration pour le stockage des vidéos
UPLOAD_DIR = Path("uploads/videos")
RESULTS_DIR = Path("results/videos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Logging
logger = logging.getLogger("video_api")

# Création du router
video_router = APIRouter(
    prefix="/api/video",
    tags=["video analysis"],
    responses={401: {"description": "Non autorisé"}},
)

# Stockage en mémoire des tâches en cours
video_tasks = {}

# Classe pour suivre la progression
class ProgressTracker:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.progress = 0
        self.message = "Initializing..."
        
    def __call__(self, progress: float, desc: str = None):
        self.progress = float(progress) * 100
        if desc:
            self.message = desc
        
        # Mettre à jour l'état de la tâche
        if self.task_id in video_tasks:
            video_tasks[self.task_id]["progress"] = self.progress
            video_tasks[self.task_id]["message"] = self.message

# Fonction pour vérifier si l'extension est autorisée
def is_allowed_video_file(filename: str) -> bool:
    allowed_extensions = [".mp4", ".avi", ".mov", ".mkv", ".webm"]
    return any(filename.lower().endswith(ext) for ext in allowed_extensions)

# Fonction pour sauvegarder une vidéo uploadée
async def save_uploaded_video(file: UploadFile) -> str:
    if not is_allowed_video_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Format de fichier non autorisé. Formats acceptés: .mp4, .avi, .mov, .mkv, .webm"
        )
    
    # Générer un nom de fichier unique
    file_extension = os.path.splitext(file.filename)[1].lower()
    filename = f"{uuid.uuid4().hex}{file_extension}"
    file_path = UPLOAD_DIR / filename
    
    # Sauvegarder le fichier
    async with aiofiles.open(file_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)
    
    return str(file_path)

# Fonction pour traiter l'analyse de manipulation vidéo
async def process_manipulation_analysis(
    task_id: str,
    video_path: str,
    api_key_info: Any
):
    progress_tracker = ProgressTracker(task_id)
    
    try:
        # Mettre à jour l'état de la tâche
        video_tasks[task_id]["status"] = "running"
        video_tasks[task_id]["started_at"] = time.time()
        
        # Étape 1 : Extraction du contenu vidéo
        start_time = time.time()
        extraction_text, extraction_path = extract_video_content(video_path, progress_tracker)
        
        if extraction_path is None:
            raise Exception(f"Échec de l'extraction: {extraction_text}")
        
        # Mettre à jour la progression
        progress_tracker(0.5, "Starting manipulation strategy analysis...")
        
        # Étape 2 : Analyse des stratégies de manipulation
        analysis = analyze_manipulation_strategies(extraction_text, extraction_path, progress_tracker)
        
        # Nettoyer le fichier temporaire
        if extraction_path and os.path.exists(extraction_path):
            os.unlink(extraction_path)
        
        # Sauvegarder les résultats
        result_file = RESULTS_DIR / f"{task_id}_manipulation_analysis.json"
        results = {
            "extraction": extraction_text,
            "analysis": analysis,
            "processing_time": time.time() - start_time
        }
        
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # Mettre à jour l'état de la tâche
        video_tasks[task_id].update({
            "status": "completed",
            "results": results,
            "completed_at": time.time(),
            "message": "Analysis complete",
            "progress": 100,
            "result_file": str(result_file)
        })
        
        logger.info(f"Tâche d'analyse de manipulation vidéo {task_id} terminée avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse de manipulation vidéo {task_id}: {str(e)}")
        video_tasks[task_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": time.time(),
            "message": f"Error: {str(e)}",
            "progress": 100
        })
        
        # Supprimer le fichier vidéo en cas d'erreur
        try:
            if os.path.exists(video_path):
                os.unlink(video_path)
        except Exception:
            pass

# Fonction pour traiter l'analyse non-verbale
async def process_nonverbal_analysis(
    task_id: str,
    video_path: str,
    api_key_info: Any
):
    progress_tracker = ProgressTracker(task_id)
    
    try:
        # Mettre à jour l'état de la tâche
        video_tasks[task_id]["status"] = "running"
        video_tasks[task_id]["started_at"] = time.time()
        
        # Étape 1 : Extraction des indices non-verbaux
        start_time = time.time()
        extraction_text, extraction_path = extract_nonverbal(video_path, progress_tracker)
        
        if extraction_path is None:
            raise Exception(f"Échec de l'extraction: {extraction_text}")
        
        # Mettre à jour la progression
        progress_tracker(0.5, "Starting non-verbal behavior analysis...")
        
        # Étape 2 : Analyse des comportements non-verbaux
        analysis = analyze_nonverbal(extraction_text, extraction_path, progress_tracker)
        
        # Nettoyer le fichier temporaire
        if extraction_path and os.path.exists(extraction_path):
            os.unlink(extraction_path)
        
        # Sauvegarder les résultats
        result_file = RESULTS_DIR / f"{task_id}_nonverbal_analysis.json"
        results = {
            "extraction": extraction_text,
            "analysis": analysis,
            "processing_time": time.time() - start_time
        }
        
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # Mettre à jour l'état de la tâche
        video_tasks[task_id].update({
            "status": "completed",
            "results": results,
            "completed_at": time.time(),
            "message": "Analysis complete",
            "progress": 100,
            "result_file": str(result_file)
        })
        
        logger.info(f"Tâche d'analyse non-verbale {task_id} terminée avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse non-verbale {task_id}: {str(e)}")
        video_tasks[task_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": time.time(),
            "message": f"Error: {str(e)}",
            "progress": 100
        })
        
        # Supprimer le fichier vidéo en cas d'erreur
        try:
            if os.path.exists(video_path):
                os.unlink(video_path)
        except Exception:
            pass

@video_router.post("/manipulation-analysis", tags=["video analysis"])
async def start_manipulation_analysis(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    keep_video: bool = Form(False),
    api_key_info = Depends(validate_api_key)
):
    """
    Démarre une analyse des stratégies de manipulation dans une vidéo.
    
    Args:
        file: Fichier vidéo à analyser
        keep_video: Si True, conserve la vidéo après l'analyse
        
    Returns:
        Un objet de réponse avec l'ID de la tâche pour vérifier l'état plus tard
    """
    # Vérifier l'autorisation pour les modèles avancés (cette analyse est considérée comme avancée)
    authorize_advanced_models(api_key_info)
    
    # Sauvegarder la vidéo uploadée
    video_path = await save_uploaded_video(file)
    
    # Générer un ID de tâche
    task_id = str(uuid.uuid4())
    
    # Enregistrer la nouvelle tâche
    video_tasks[task_id] = {
        "type": "manipulation-analysis",
        "status": "pending",
        "video_path": video_path,
        "filename": file.filename,
        "created_at": time.time(),
        "keep_video": keep_video,
        "message": "Task queued",
        "progress": 0,
        "user_id": api_key_info.user_id,
        "api_key_id": api_key_info.id
    }
    
    # Lancer la tâche en arrière-plan
    background_tasks.add_task(
        process_manipulation_analysis,
        task_id=task_id,
        video_path=video_path,
        api_key_info=api_key_info
    )
    
    # Enregistrer l'utilisation
    usage_record = UsageRecord(
        user_id=api_key_info.user_id,
        api_key_id=api_key_info.key,
        request_path="/api/video/manipulation-analysis",
        request_method="POST",
        tokens_input=0,  # À compléter plus tard
        tokens_output=0,  # À compléter plus tard
        processing_time=0.0,  # À mettre à jour une fois terminé
        status_code=200
    )
    record_api_usage(usage_record)
    
    logger.info(f"Tâche d'analyse de manipulation vidéo créée avec ID: {task_id}")
    
    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Video manipulation analysis task started"
    }

@video_router.post("/nonverbal-analysis", tags=["video analysis"])
async def start_nonverbal_analysis(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    keep_video: bool = Form(False),
    api_key_info = Depends(validate_api_key)
):
    """
    Démarre une analyse des comportements non-verbaux dans une vidéo.
    
    Args:
        file: Fichier vidéo à analyser
        keep_video: Si True, conserve la vidéo après l'analyse
        
    Returns:
        Un objet de réponse avec l'ID de la tâche pour vérifier l'état plus tard
    """
    # Vérifier l'autorisation pour les modèles avancés (cette analyse est considérée comme avancée)
    authorize_advanced_models(api_key_info)
    
    # Sauvegarder la vidéo uploadée
    video_path = await save_uploaded_video(file)
    
    # Générer un ID de tâche
    task_id = str(uuid.uuid4())
    
    # Enregistrer la nouvelle tâche
    video_tasks[task_id] = {
        "type": "nonverbal-analysis",
        "status": "pending",
        "video_path": video_path,
        "filename": file.filename,
        "created_at": time.time(),
        "keep_video": keep_video,
        "message": "Task queued",
        "progress": 0,
        "user_id": api_key_info.user_id,
        "api_key_id": api_key_info.id
    }
    
    # Lancer la tâche en arrière-plan
    background_tasks.add_task(
        process_nonverbal_analysis,
        task_id=task_id,
        video_path=video_path,
        api_key_info=api_key_info
    )
    
    # Enregistrer l'utilisation
    usage_record = UsageRecord(
        user_id=api_key_info.user_id,
        api_key_id=api_key_info.key,
        request_path="/api/video/nonverbal-analysis",
        request_method="POST",
        tokens_input=0,  # À compléter plus tard
        tokens_output=0,  # À compléter plus tard
        processing_time=0.0,  # À mettre à jour une fois terminé
        status_code=200
    )
    record_api_usage(usage_record)
    
    logger.info(f"Tâche d'analyse non-verbale créée avec ID: {task_id}")
    
    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Non-verbal behavior analysis task started"
    }

@video_router.get("/tasks/{task_id}", tags=["video analysis"])
async def get_video_task_status(
    task_id: str,
    api_key_info = Depends(validate_api_key)
):
    """
    Vérifie l'état d'une tâche d'analyse vidéo.
    
    Args:
        task_id: L'identifiant de la tâche
        
    Returns:
        L'état actuel de la tâche d'analyse vidéo
    """
    if task_id not in video_tasks:
        raise HTTPException(status_code=404, detail=f"Tâche {task_id} non trouvée")
    
    task_info = video_tasks[task_id]
    
    # Vérifier si la tâche appartient à l'utilisateur associé à la clé API
    if task_info.get("user_id") != api_key_info.user_id:
        raise HTTPException(
            status_code=403,
            detail="Vous n'avez pas accès à cette tâche"
        )
    
    # Préparer la réponse
    response = {
        "task_id": task_id,
        "type": task_info.get("type"),
        "status": task_info.get("status"),
        "message": task_info.get("message"),
        "progress": task_info.get("progress", 0),
        "filename": task_info.get("filename"),
        "created_at": task_info.get("created_at"),
        "started_at": task_info.get("started_at"),
        "completed_at": task_info.get("completed_at")
    }
    
    # Ajouter les résultats si la tâche est terminée
    if task_info.get("status") == "completed":
        response["results"] = task_info.get("results")
        response["result_file"] = task_info.get("result_file")
        
    # Ajouter les informations d'erreur si la tâche a échoué
    elif task_info.get("status") == "failed":
        response["error"] = task_info.get("error")
        
    return response

@video_router.get("/tasks", tags=["video analysis"])
async def list_video_tasks(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, regex="^(pending|running|completed|failed)$"),
    type: Optional[str] = Query(None, regex="^(manipulation-analysis|nonverbal-analysis)$"),
    api_key_info = Depends(validate_api_key)
):
    """
    Liste les tâches d'analyse vidéo de l'utilisateur.
    
    Args:
        limit: Nombre maximum de tâches à retourner
        offset: Décalage pour la pagination
        status: Filtrer par statut (pending, running, completed, failed)
        type: Filtrer par type d'analyse
        
    Returns:
        Liste des tâches d'analyse vidéo
    """
    # Filtrer les tâches par utilisateur
    user_tasks = {
        k: v for k, v in video_tasks.items()
        if v.get("user_id") == api_key_info.user_id
    }
    
    # Filtrer par statut si spécifié
    if status:
        user_tasks = {
            k: v for k, v in user_tasks.items()
            if v.get("status") == status
        }
        
    # Filtrer par type si spécifié
    if type:
        user_tasks = {
            k: v for k, v in user_tasks.items()
            if v.get("type") == type
        }
    
    # Trier par date de création (plus récent en premier)
    sorted_tasks = sorted(
        user_tasks.items(),
        key=lambda x: x[1].get("created_at", 0),
        reverse=True
    )
    
    # Appliquer la pagination
    paginated_tasks = sorted_tasks[offset:offset+limit]
    
    # Préparer la réponse
    response = {
        "total": len(user_tasks),
        "limit": limit,
        "offset": offset,
        "tasks": {}
    }
    
    for task_id, task_info in paginated_tasks:
        response["tasks"][task_id] = {
            "type": task_info.get("type"),
            "status": task_info.get("status"),
            "message": task_info.get("message"),
            "progress": task_info.get("progress", 0),
            "filename": task_info.get("filename"),
            "created_at": task_info.get("created_at"),
            "completed_at": task_info.get("completed_at", None)
        }
    
    return response

@video_router.delete("/tasks/{task_id}", tags=["video analysis"])
async def delete_video_task(
    task_id: str,
    api_key_info = Depends(validate_api_key)
):
    """
    Supprime une tâche d'analyse vidéo et ses résultats.
    
    Args:
        task_id: L'identifiant de la tâche
        
    Returns:
        Message de confirmation
    """
    if task_id not in video_tasks:
        raise HTTPException(status_code=404, detail=f"Tâche {task_id} non trouvée")
    
    task_info = video_tasks[task_id]
    
    # Vérifier si la tâche appartient à l'utilisateur associé à la clé API
    if task_info.get("user_id") != api_key_info.user_id:
        raise HTTPException(
            status_code=403,
            detail="Vous n'avez pas accès à cette tâche"
        )
    
    # Supprimer le fichier vidéo si existant et non conservé
    if not task_info.get("keep_video", False) and "video_path" in task_info:
        video_path = task_info["video_path"]
        if os.path.exists(video_path):
            try:
                os.unlink(video_path)
            except Exception as e:
                logger.warning(f"Erreur lors de la suppression de la vidéo {video_path}: {str(e)}")
    
    # Supprimer le fichier de résultats si existant
    if "result_file" in task_info:
        result_file = task_info["result_file"]
        if os.path.exists(result_file):
            try:
                os.unlink(result_file)
            except Exception as e:
                logger.warning(f"Erreur lors de la suppression du fichier de résultats {result_file}: {str(e)}")
    
    # Supprimer la tâche
    del video_tasks[task_id]
    
    return {
        "message": f"Tâche {task_id} supprimée avec succès"
    }