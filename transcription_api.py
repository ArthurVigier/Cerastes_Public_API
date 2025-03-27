from fastapi import APIRouter, File, UploadFile, BackgroundTasks, HTTPException, Depends, Form, Request, Query
from fastapi.responses import JSONResponse, FileResponse
from typing import Dict, List, Optional, Union, Any
import os
import uuid
import time
import json
import aiofiles
import logging
from tempfile import NamedTemporaryFile
from pathlib import Path

# Import des fonctions de transcription
from transcription_utils import process_monologue, process_multiple_speakers

# Import des dépendances d'authentification
from auth import validate_api_key, authorize_advanced_models
from database import record_api_usage
from auth_models import UsageRecord

# Configuration pour le stockage des vidéos et transcriptions
UPLOAD_DIR = Path("uploads/videos")
RESULTS_DIR = Path("results/transcriptions")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Logging
logger = logging.getLogger("transcription_api")

# Création du router
transcription_router = APIRouter(
    prefix="/api/transcription",
    tags=["video transcription"],
    responses={401: {"description": "Non autorisé"}},
)

# Stockage en mémoire des tâches en cours
transcription_tasks = {}

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
        if self.task_id in transcription_tasks:
            transcription_tasks[self.task_id]["progress"] = self.progress
            transcription_tasks[self.task_id]["message"] = self.message

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

# Fonction pour traiter une transcription monologue
async def process_transcription_monologue(
    task_id: str,
    video_path: str,
    model_size: str,
    keep_video: bool,
    api_key_info: Any
):
    progress_tracker = ProgressTracker(task_id)
    
    try:
        # Mettre à jour l'état de la tâche
        transcription_tasks[task_id]["status"] = "running"
        transcription_tasks[task_id]["started_at"] = time.time()
        
        # Chemin pour le fichier de sortie
        output_txt = RESULTS_DIR / f"{task_id}_monologue.txt"
        
        # Exécuter la transcription
        start_time = time.time()
        result = process_monologue(
            video_path, 
            str(output_txt), 
            model_size, 
            progress=progress_tracker
        )
        
        # Créer un fichier JSON avec les résultats détaillés
        result_file = RESULTS_DIR / f"{task_id}_monologue.json"
        results = {
            "transcription": result["transcription"],
            "segments": result["segments"],
            "processing_time": time.time() - start_time
        }
        
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # Mettre à jour l'état de la tâche
        transcription_tasks[task_id].update({
            "status": "completed",
            "results": results,
            "completed_at": time.time(),
            "message": "Transcription complete",
            "progress": 100,
            "result_file": str(result_file),
            "text_file": str(output_txt)
        })
        
        logger.info(f"Tâche de transcription monologue {task_id} terminée avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors de la transcription monologue {task_id}: {str(e)}")
        transcription_tasks[task_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": time.time(),
            "message": f"Error: {str(e)}",
            "progress": 100
        })
    
    finally:
        # Supprimer le fichier vidéo si demandé
        if not keep_video and os.path.exists(video_path):
            try:
                os.unlink(video_path)
            except Exception as e:
                logger.warning(f"Impossible de supprimer le fichier vidéo {video_path}: {str(e)}")

# Fonction pour traiter une transcription avec identification des locuteurs
async def process_transcription_multispeaker(
    task_id: str,
    video_path: str,
    model_size: str,
    huggingface_token: str,
    keep_video: bool,
    api_key_info: Any
):
    progress_tracker = ProgressTracker(task_id)
    
    try:
        # Mettre à jour l'état de la tâche
        transcription_tasks[task_id]["status"] = "running"
        transcription_tasks[task_id]["started_at"] = time.time()
        
        # Chemin pour le fichier de sortie
        output_txt = RESULTS_DIR / f"{task_id}_multispeaker.txt"
        
        # Exécuter la transcription avec identification des locuteurs
        start_time = time.time()
        result = process_multiple_speakers(
            video_path, 
            str(output_txt), 
            model_size, 
            huggingface_token, 
            progress=progress_tracker
        )
        
        # Créer un fichier JSON avec les résultats détaillés
        result_file = RESULTS_DIR / f"{task_id}_multispeaker.json"
        results = {
            "segments": result["segments"],
            "processing_time": time.time() - start_time
        }
        
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # Mettre à jour l'état de la tâche
        transcription_tasks[task_id].update({
            "status": "completed",
            "results": results,
            "completed_at": time.time(),
            "message": "Transcription with speaker identification complete",
            "progress": 100,
            "result_file": str(result_file),
            "text_file": str(output_txt)
        })
        
        logger.info(f"Tâche de transcription multispeaker {task_id} terminée avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors de la transcription multispeaker {task_id}: {str(e)}")
        transcription_tasks[task_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": time.time(),
            "message": f"Error: {str(e)}",
            "progress": 100
        })
    
    finally:
        # Supprimer le fichier vidéo si demandé
        if not keep_video and os.path.exists(video_path):
            try:
                os.unlink(video_path)
            except Exception as e:
                logger.warning(f"Impossible de supprimer le fichier vidéo {video_path}: {str(e)}")

@transcription_router.post("/monologue", tags=["video transcription"])
async def start_monologue_transcription(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model_size: str = Form("medium"),
    keep_video: bool = Form(False),
    api_key_info = Depends(validate_api_key)
):
    """
    Démarre une transcription monologue (sans identification des locuteurs).
    
    Args:
        file: Fichier vidéo à transcrire
        model_size: Taille du modèle Whisper (tiny, base, small, medium, large)
        keep_video: Si True, conserve la vidéo après la transcription
        
    Returns:
        Un objet de réponse avec l'ID de la tâche pour vérifier l'état plus tard
    """
    # Vérifier l'autorisation pour les modèles avancés
    if model_size in ["large"]:
        authorize_advanced_models(api_key_info)
    
    # Sauvegarder la vidéo uploadée
    video_path = await save_uploaded_video(file)
    
    # Générer un ID de tâche
    task_id = str(uuid.uuid4())
    
    # Enregistrer la nouvelle tâche
    transcription_tasks[task_id] = {
        "type": "monologue",
        "status": "pending",
        "video_path": video_path,
        "filename": file.filename,
        "created_at": time.time(),
        "keep_video": keep_video,
        "model_size": model_size,
        "message": "Task queued",
        "progress": 0,
        "user_id": api_key_info.user_id,
        "api_key_id": api_key_info.id
    }
    
    # Lancer la tâche en arrière-plan
    background_tasks.add_task(
        process_transcription_monologue,
        task_id=task_id,
        video_path=video_path,
        model_size=model_size,
        keep_video=keep_video,
        api_key_info=api_key_info
    )
    
    # Enregistrer l'utilisation
    usage_record = UsageRecord(
        user_id=api_key_info.user_id,
        api_key_id=api_key_info.key,
        request_path="/api/transcription/monologue",
        request_method="POST",
        tokens_input=0,  # À compléter plus tard
        tokens_output=0,  # À compléter plus tard
        processing_time=0.0,  # À mettre à jour une fois terminé
        status_code=200
    )
    record_api_usage(usage_record)
    
    logger.info(f"Tâche de transcription monologue créée avec ID: {task_id}")
    
    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Monologue transcription task started"
    }

@transcription_router.post("/multispeaker", tags=["video transcription"])
async def start_multispeaker_transcription(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model_size: str = Form("medium"),
    huggingface_token: str = Form(None),
    keep_video: bool = Form(False),
    api_key_info = Depends(validate_api_key)
):
    """
    Démarre une transcription avec identification des locuteurs.
    
    Args:
        file: Fichier vidéo à transcrire
        model_size: Taille du modèle Whisper (tiny, base, small, medium, large)
        huggingface_token: Token Hugging Face pour l'accès au modèle (facultatif)
        keep_video: Si True, conserve la vidéo après la transcription
        
    Returns:
        Un objet de réponse avec l'ID de la tâche pour vérifier l'état plus tard
    """
    # Vérifier l'autorisation pour les modèles avancés (cette analyse est toujours considérée comme avancée)
    authorize_advanced_models(api_key_info)
    
    # Vérifier la présence d'un token Hugging Face
    if not huggingface_token and not os.environ.get("HUGGINGFACE_TOKEN"):
        raise HTTPException(
            status_code=400,
            detail="Un token Hugging Face est requis pour l'identification des locuteurs. Fournissez-le dans la requête ou définissez la variable d'environnement HUGGINGFACE_TOKEN."
        )
    
    # Sauvegarder la vidéo uploadée
    video_path = await save_uploaded_video(file)
    
    # Générer un ID de tâche
    task_id = str(uuid.uuid4())
    
    # Enregistrer la nouvelle tâche
    transcription_tasks[task_id] = {
        "type": "multispeaker",
        "status": "pending",
        "video_path": video_path,
        "filename": file.filename,
        "created_at": time.time(),
        "keep_video": keep_video,
        "model_size": model_size,
        "huggingface_token": "[REDACTED]" if huggingface_token else None,
        "message": "Task queued",
        "progress": 0,
        "user_id": api_key_info.user_id,
        "api_key_id": api_key_info.id
    }
    
    # Lancer la tâche en arrière-plan
    background_tasks.add_task(
        process_transcription_multispeaker,
        task_id=task_id,
        video_path=video_path,
        model_size=model_size,
        huggingface_token=huggingface_token,
        keep_video=keep_video,
        api_key_info=api_key_info
    )
    
    # Enregistrer l'utilisation
    usage_record = UsageRecord(
        user_id=api_key_info.user_id,
        api_key_id=api_key_info.key,
        request_path="/api/transcription/multispeaker",
        request_method="POST",
        tokens_input=0,  # À compléter plus tard
        tokens_output=0,  # À compléter plus tard
        processing_time=0.0,  # À mettre à jour une fois terminé
        status_code=200
    )
    record_api_usage(usage_record)
    
    logger.info(f"Tâche de transcription multispeaker créée avec ID: {task_id}")
    
    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Multi-speaker transcription task started"
    }

@transcription_router.get("/tasks/{task_id}", tags=["video transcription"])
async def get_transcription_task_status(
    task_id: str,
    api_key_info = Depends(validate_api_key)
):
    """
    Vérifie l'état d'une tâche de transcription.
    
    Args:
        task_id: L'identifiant de la tâche
        
    Returns:
        L'état actuel de la tâche de transcription
    """
    if task_id not in transcription_tasks:
        raise HTTPException(status_code=404, detail=f"Tâche {task_id} non trouvée")
    
    task_info = transcription_tasks[task_id]
    
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
        "model_size": task_info.get("model_size"),
        "created_at": task_info.get("created_at"),
        "started_at": task_info.get("started_at"),
        "completed_at": task_info.get("completed_at")
    }
    
    # Ajouter les résultats si la tâche est terminée
    if task_info.get("status") == "completed":
        response["results"] = task_info.get("results")
        response["result_file"] = task_info.get("result_file")
        response["text_file"] = task_info.get("text_file")
    elif task_info.get("status") == "failed":
        response["error"] = task_info.get("error")
        response["error_type"] = task_info.get("error_type")
        response["message"] = task_info.get("message")
        response["progress"] = 100
        response["completed_at"] = task_info.get("completed_at")
    else:
        response["message"] = task_info.get("message")
        response["progress"] = task_info.get("progress", 0)
        response["created_at"] = task_info.get("created_at")
        response["started_at"] = task_info.get("started_at")
        response["completed_at"] = task_info.get("completed_at")
        response["result_file"] = task_info.get("result_file")
        response["text_file"] = task_info.get("text_file")
    return JSONResponse(response)

@transcription_router.get("/tasks/{task_id}", tags=["video transcription"])
async def get_transcription_task_status(
    task_id: str,
    api_key_info = Depends(validate_api_key)
):
    """
    Vérifie l'état d'une tâche de transcription.
    
    Args:
        task_id: L'identifiant de la tâche
        
    Returns:
        L'état actuel de la tâche de transcription
    """
    if task_id not in transcription_tasks:
        raise HTTPException(status_code=404, detail=f"Tâche {task_id} non trouvée")
    
    task_info = transcription_tasks[task_id]
    
    # Vérifier si la tâche appartient à l'utilisateur associé à la clé API
    if task_info.get("user_id") != api_key_info.user_id:
        raise HTTPException(
            status_code=403,
            detail="Vous n'avez pas accès à cette tâche"
        )
    
    # Préparer la réponse de base
    response = {
        "task_id": task_id,
        "type": task_info.get("type"),
        "status": task_info.get("status"),
        "message": task_info.get("message"),
        "progress": task_info.get("progress", 0),
        "filename": task_info.get("filename"),
        "model_size": task_info.get("model_size"),
        "created_at": task_info.get("created_at"),
        "started_at": task_info.get("started_at"),
        "completed_at": task_info.get("completed_at")
    }
    
    # Ajouter les résultats si la tâche est terminée ou échouée
    if task_info.get("status") == "completed":
        response["results"] = task_info.get("results")
        response["result_file"] = task_info.get("result_file")
        response["text_file"] = task_info.get("text_file")
    elif task_info.get("status") == "failed":
        response["error"] = task_info.get("error")
    
    return JSONResponse(response)


@transcription_router.get("/download/{task_id}/{file_type}", tags=["video transcription"])
async def download_file(
    task_id: str, 
    file_type: str, 
    api_key_info = Depends(validate_api_key)
):
    """
    Permet de télécharger le fichier de transcription associé à une tâche.
    
    Args:
        task_id: Identifiant de la tâche.
        file_type: Type de fichier à télécharger ("text" ou "json").
        
    Returns:
        Un FileResponse contenant le fichier demandé.
    """
    if task_id not in transcription_tasks:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    
    task_info = transcription_tasks[task_id]
    
    # Vérifier si la tâche appartient à l'utilisateur
    if task_info.get("user_id") != api_key_info.user_id:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    if file_type == "text":
        file_path = task_info.get("text_file")
    elif file_type == "json":
        file_path = task_info.get("result_file")
    else:
        raise HTTPException(status_code=400, detail="Type de fichier non valide. Utilisez 'text' ou 'json'.")
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Fichier non trouvé")
    
    return FileResponse(file_path, filename=os.path.basename(file_path))


@transcription_router.get("/tasks", tags=["video transcription"])
async def list_user_tasks(api_key_info = Depends(validate_api_key)):
    """
    Liste toutes les tâches de transcription pour l'utilisateur connecté.
    
    Returns:
        Une liste de tâches avec leurs états.
    """
    user_tasks = [
        {
            "task_id": task_id,
            "type": info.get("type"),
            "status": info.get("status"),
            "message": info.get("message"),
            "progress": info.get("progress", 0),
            "filename": info.get("filename"),
            "model_size": info.get("model_size"),
            "created_at": info.get("created_at"),
            "started_at": info.get("started_at"),
            "completed_at": info.get("completed_at")
        }
        for task_id, info in transcription_tasks.items() if info.get("user_id") == api_key_info.user_id
    ]
    return JSONResponse({"tasks": user_tasks})