"""
Module d'utilisation de Whisper pour la transcription audio
----------------------------------------------------------
Ce module fournit des fonctions pour la transcription audio avec le modèle Whisper.
"""

import os
import gc
import logging
import traceback
from typing import Dict, Any, Optional, Callable, Union

# Logging
logger = logging.getLogger("transcription.whisper")

# Vérifier les dépendances
try:
    import whisper
    import torch
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("Whisper n'est pas disponible. La transcription sera désactivée.")

# Modèle global pour réutilisation
whisper_model = None
current_model_size = None

# Configuration
WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "medium")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def get_whisper_model(model_size: Optional[str] = None) -> Any:
    """
    Charge ou récupère le modèle Whisper
    
    Args:
        model_size: Taille du modèle Whisper à utiliser ('tiny', 'base', 'small', 'medium', 'large')
        
    Returns:
        Instance du modèle Whisper
        
    Raises:
        ImportError: Si Whisper n'est pas disponible
    """
    global whisper_model, current_model_size
    
    if not WHISPER_AVAILABLE:
        raise ImportError("Whisper est requis pour la transcription")
    
    # Définir la taille du modèle
    selected_size = model_size or WHISPER_MODEL_SIZE
    
    # Vérifier si nous devons charger un nouveau modèle
    if whisper_model is None or current_model_size != selected_size:
        # Libérer la mémoire si un modèle était déjà chargé
        if whisper_model is not None:
            del whisper_model
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        
        logger.info(f"Chargement du modèle Whisper {selected_size}...")
        whisper_model = whisper.load_model(selected_size, device=DEVICE)
        current_model_size = selected_size
        
    return whisper_model

def transcribe_audio(
    audio_path: str, 
    model_size: Optional[str] = None, 
    language: Optional[str] = None,
    progress: Optional[Callable] = None,
    **whisper_options
) -> Dict[str, Any]:
    """
    Transcrit un fichier audio en texte
    
    Args:
        audio_path: Chemin vers le fichier audio
        model_size: Taille du modèle Whisper à utiliser
        language: Code de langue pour la transcription (ex: 'fr', 'en')
        progress: Fonction de suivi de progression (facultatif)
        whisper_options: Options supplémentaires à passer à Whisper
        
    Returns:
        Dictionnaire contenant les résultats de la transcription
        
    Raises:
        ImportError: Si Whisper n'est pas disponible
        Exception: Si une erreur survient pendant la transcription
    """
    try:
        if progress:
            progress(0.4, desc="Chargement du modèle de transcription...")
        
        # Charger le modèle Whisper
        model = get_whisper_model(model_size)
        
        if progress:
            progress(0.5, desc="Transcription audio en cours...")
        
        # Préparer les options de transcription
        options = {
            "fp16": torch.cuda.is_available(),
            "verbose": False
        }
        
        # Ajouter la langue si spécifiée
        if language:
            options["language"] = language
            
        # Ajouter les options supplémentaires
        options.update(whisper_options)
        
        # Transcrire l'audio
        result = model.transcribe(audio_path, **options)
        
        if progress:
            progress(0.8, desc="Transcription terminée")
        
        return result
        
    except Exception as e:
        error_msg = f"Erreur lors de la transcription: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise Exception(error_msg)

def cleanup_whisper_model() -> bool:
    """
    Libère la mémoire du modèle Whisper
    
    Returns:
        True si le modèle a été libéré, False sinon
    """
    global whisper_model, current_model_size
    
    if whisper_model is not None:
        try:
            del whisper_model
            whisper_model = None
            current_model_size = None
            gc.collect()
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la libération du modèle Whisper: {str(e)}")
            
    return False

def get_available_whisper_models() -> Dict[str, Dict[str, Any]]:
    """
    Retourne les modèles Whisper disponibles avec leurs caractéristiques
    
    Returns:
        Dictionnaire des modèles disponibles
    """
    if not WHISPER_AVAILABLE:
        return {}
        
    return {
        "tiny": {"parameters": "39M", "english_only": False, "multilingual": True, "required_vram": "1 GB"},
        "base": {"parameters": "74M", "english_only": False, "multilingual": True, "required_vram": "1 GB"},
        "small": {"parameters": "244M", "english_only": False, "multilingual": True, "required_vram": "2 GB"},
        "medium": {"parameters": "769M", "english_only": False, "multilingual": True, "required_vram": "5 GB"},
        "large": {"parameters": "1550M", "english_only": False, "multilingual": True, "required_vram": "10 GB"}
    }

def format_whisper_result(result: Dict[str, Any], include_timestamps: bool = True) -> str:
    """
    Formate le résultat de Whisper en texte lisible
    
    Args:
        result: Résultat de la transcription Whisper
        include_timestamps: Inclure les horodatages dans la sortie
        
    Returns:
        Texte formaté
    """
    if not include_timestamps:
        return result["text"].strip()
    
    formatted_text = []
    for segment in result["segments"]:
        start = format_time(segment["start"])
        end = format_time(segment["end"])
        text = segment["text"].strip()
        formatted_text.append(f"[{start}-{end}] {text}")
    
    return "\n".join(formatted_text)

def format_time(seconds: float) -> str:
    """
    Formate les secondes en format hh:mm:ss
    
    Args:
        seconds: Nombre de secondes
        
    Returns:
        Chaîne formatée
    """
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"