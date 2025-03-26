"""
Module principal pour la transcription de fichiers vidéo et audio
----------------------------------------------------------------
Ce module intègre les fonctionnalités des autres modules de transcription
pour fournir une API unifiée pour la transcription de contenu multimédia.
"""

import os
import json
import logging
import time
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
from tempfile import NamedTemporaryFile

# Import des modules spécialisés
from .audio_extraction import extract_audio, cleanup_audio_file
from .whisper_utils import transcribe_audio, format_whisper_result, cleanup_whisper_model
from .diarization import diarize_audio, assign_speakers, format_diarized_transcription

# Configuration du logging
logger = logging.getLogger("transcription.core")

# Répertoire temporaire pour les fichiers de sortie
RESULTS_DIR = Path("results/transcriptions")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def process_monologue(
    video_path: str, 
    output_txt: Optional[str] = None, 
    model_size: Optional[str] = None, 
    progress: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Transcrit une vidéo en mode monologue (sans identification des locuteurs)
    
    Args:
        video_path: Chemin vers le fichier vidéo
        output_txt: Chemin de sortie pour le fichier texte (facultatif)
        model_size: Taille du modèle Whisper à utiliser
        progress: Fonction de suivi de progression (facultatif)
        
    Returns:
        Dictionnaire contenant la transcription complète et les segments
        
    Raises:
        Exception: Si une erreur survient pendant le traitement
    """
    try:
        # Extraire l'audio
        if progress:
            progress(0.1, desc="Extraction de l'audio...")
        
        audio_path = extract_audio(video_path, progress=progress)
        audio_extracted = True
        
        # Transcrire l'audio
        if progress:
            progress(0.3, desc="Transcription en cours...")
        
        result = transcribe_audio(audio_path, model_size, progress=progress)
        
        # Sauvegarder la transcription si demandé
        if output_txt:
            with open(output_txt, "w", encoding="utf-8") as f:
                formatted_text = format_whisper_result(result)
                f.write(formatted_text)
            
            if progress:
                progress(0.95, desc=f"Transcription enregistrée dans {output_txt}")
        
        # Nettoyage
        if progress:
            progress(1.0, desc="Transcription terminée")
        
        if audio_extracted:
            cleanup_audio_file(audio_path)
        
        # Format de sortie unifié
        return {
            "transcription": result["text"],
            "segments": result["segments"],
            "language": result.get("language", ""),
            "duration": result.get("duration", 0)
        }
        
    except Exception as e:
        error_msg = f"Erreur lors de la transcription: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        # Nettoyage en cas d'erreur
        if 'audio_path' in locals() and 'audio_extracted' in locals() and audio_extracted:
            cleanup_audio_file(audio_path)
        
        raise Exception(error_msg)

def process_multiple_speakers(
    video_path: str, 
    output_txt: Optional[str] = None, 
    model_size: Optional[str] = None, 
    huggingface_token: Optional[str] = None, 
    progress: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Transcrit une vidéo avec identification des locuteurs
    
    Args:
        video_path: Chemin vers le fichier vidéo
        output_txt: Chemin de sortie pour le fichier texte (facultatif)
        model_size: Taille du modèle Whisper à utiliser
        huggingface_token: Token Hugging Face pour l'accès au modèle de diarisation
        progress: Fonction de suivi de progression (facultatif)
        
    Returns:
        Dictionnaire contenant la transcription avec identification des locuteurs
        
    Raises:
        Exception: Si une erreur survient pendant le traitement
    """
    try:
        # Extraire l'audio
        if progress:
            progress(0.1, desc="Extraction de l'audio...")
        
        audio_path = extract_audio(video_path, progress=progress)
        audio_extracted = True
        
        # Transcrire l'audio
        if progress:
            progress(0.3, desc="Transcription en cours...")
        
        result = transcribe_audio(audio_path, model_size, progress=progress)
        
        # Identifier les locuteurs
        if progress:
            progress(0.5, desc="Identification des locuteurs en cours...")
        
        diarization = diarize_audio(audio_path, huggingface_token, progress=progress)
        
        # Associer les locuteurs à la transcription
        final_transcription = assign_speakers(result, diarization)
        
        # Sauvegarder le résultat si demandé
        if output_txt:
            with open(output_txt, "w", encoding="utf-8") as f:
                formatted_text = format_diarized_transcription(final_transcription)
                f.write(formatted_text)
            
            if progress:
                progress(0.95, desc=f"Transcription enregistrée dans {output_txt}")
        
        # Nettoyage
        if progress:
            progress(1.0, desc="Transcription terminée")
        
        if audio_extracted:
            cleanup_audio_file(audio_path)
        
        # Format de sortie unifié
        return {
            "transcription": format_diarized_transcription(final_transcription, include_timestamps=False),
            "segments": final_transcription,
            "language": result.get("language", ""),
            "duration": result.get("duration", 0),
            "speakers": list(set(segment["speaker"] for segment in final_transcription))
        }
        
    except Exception as e:
        error_msg = f"Erreur lors de la transcription avec identification des locuteurs: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        # Nettoyage en cas d'erreur
        if 'audio_path' in locals() and 'audio_extracted' in locals() and audio_extracted:
            cleanup_audio_file(audio_path)
        
        # Libérer la mémoire des modèles
        cleanup_whisper_model()
        
        raise Exception(error_msg)

def transcribe_external_audio(
    audio_path: str,
    model_size: Optional[str] = None,
    output_txt: Optional[str] = None,
    progress: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Transcrit un fichier audio existant sans extraction
    
    Args:
        audio_path: Chemin vers le fichier audio
        model_size: Taille du modèle Whisper à utiliser
        output_txt: Chemin de sortie pour le fichier texte (facultatif)
        progress: Fonction de suivi de progression (facultatif)
        
    Returns:
        Dictionnaire contenant la transcription complète et les segments
        
    Raises:
        Exception: Si une erreur survient pendant le traitement
    """
    try:
        # Transcrire l'audio
        if progress:
            progress(0.2, desc="Transcription audio en cours...")
        
        result = transcribe_audio(audio_path, model_size, progress=progress)
        
        # Sauvegarder la transcription si demandé
        if output_txt:
            with open(output_txt, "w", encoding="utf-8") as f:
                formatted_text = format_whisper_result(result)
                f.write(formatted_text)
            
            if progress:
                progress(0.9, desc=f"Transcription enregistrée dans {output_txt}")
        
        if progress:
            progress(1.0, desc="Transcription terminée")
        
        # Format de sortie unifié
        return {
            "transcription": result["text"],
            "segments": result["segments"],
            "language": result.get("language", ""),
            "duration": result.get("duration", 0)
        }
        
    except Exception as e:
        error_msg = f"Erreur lors de la transcription audio: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise Exception(error_msg)

def get_available_models() -> Dict[str, Dict[str, Any]]:
    """
    Retourne les informations sur les modèles de transcription disponibles
    
    Returns:
        Dictionnaire avec les informations sur les modèles
    """
    from .whisper_utils import get_available_whisper_models
    
    models = {
        "whisper": get_available_whisper_models(),
        "diarization": {
            "pyannote": {
                "description": "Modèle de diarisation pour l'identification des locuteurs",
                "requires_token": True,
                "source": "https://huggingface.co/pyannote/speaker-diarization-3.1"
            }
        }
    }
    
    return models