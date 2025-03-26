"""
Module de diarisation pour la transcription vidéo
------------------------------------------------
Ce module fournit des fonctions pour l'identification des locuteurs (diarisation)
dans des fichiers audio et pour l'attribution des locuteurs aux segments de transcription.
"""

import os
import logging
import traceback
from typing import List, Dict, Tuple, Optional, Callable, Any, Union

# Configuration du logging
logger = logging.getLogger("transcription.diarization")

# Vérifier les dépendances optionnelles
try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False
    logger.warning("Pyannote.audio non disponible. La diarisation sera désactivée.")

# Configuration
HUGGINGFACE_TOKEN = os.environ.get("HUGGINGFACE_TOKEN", "")
DIARIZATION_MODEL = "pyannote/speaker-diarization-3.1"

# Variable globale pour le modèle
diarization_pipeline = None

def load_diarization_model(huggingface_token: Optional[str] = None):
    """
    Charge le modèle de diarisation
    
    Args:
        huggingface_token: Token Hugging Face pour l'accès au modèle
        
    Returns:
        Pipeline de diarisation
        
    Raises:
        ImportError: Si pyannote.audio n'est pas disponible
        ValueError: Si aucun token n'est fourni
    """
    global diarization_pipeline
    
    if not PYANNOTE_AVAILABLE:
        raise ImportError("Pyannote.audio est requis pour la diarisation")
    
    token = huggingface_token or HUGGINGFACE_TOKEN
    if not token:
        raise ValueError("Un token Hugging Face est requis pour la diarisation")
    
    if diarization_pipeline is None:
        diarization_pipeline = Pipeline.from_pretrained(
            DIARIZATION_MODEL,
            use_auth_token=token
        )
    
    return diarization_pipeline

def diarize_audio(
    audio_path: str, 
    huggingface_token: Optional[str] = None, 
    progress: Optional[Callable] = None
) -> List[Tuple[float, float, str]]:
    """
    Identifie les locuteurs dans un fichier audio
    
    Args:
        audio_path: Chemin vers le fichier audio
        huggingface_token: Token Hugging Face pour l'accès au modèle
        progress: Fonction de suivi de progression (facultatif)
        
    Returns:
        Liste de segments avec informations sur les locuteurs (start, end, speaker)
        
    Raises:
        ImportError: Si pyannote.audio n'est pas disponible
        ValueError: Si aucun token n'est fourni
        Exception: Si une erreur survient pendant la diarisation
    """
    try:
        if progress:
            progress(0.6, desc="Chargement du modèle de diarisation...")
        
        # Initialiser le pipeline de diarisation
        pipeline = load_diarization_model(huggingface_token)
        
        if progress:
            progress(0.7, desc="Identification des locuteurs en cours...")
        
        # Effectuer la diarisation
        diarization = pipeline(audio_path)
        
        # Extraire les segments avec locuteurs
        speaker_segments = []
        for segment, _, speaker in diarization.itertracks(yield_label=True):
            speaker_segments.append((segment.start, segment.end, speaker))
        
        if progress:
            progress(0.9, desc="Identification des locuteurs terminée")
        
        return speaker_segments
        
    except Exception as e:
        error_msg = f"Erreur lors de la diarisation: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise Exception(error_msg)

def assign_speakers(
    transcription: Dict[str, Any], 
    diarization: List[Tuple[float, float, str]]
) -> List[Dict[str, Any]]:
    """
    Associe les locuteurs identifiés aux segments de transcription
    
    Args:
        transcription: Résultat de la transcription avec Whisper
        diarization: Résultat de la diarisation avec Pyannote
        
    Returns:
        Liste de segments avec texte et locuteur attribué
    """
    final_transcription = []
    
    segments = transcription["segments"]
    
    for segment in segments:
        start, end, text = segment["start"], segment["end"], segment["text"]
        speaker = "Unknown"
        
        # Trouver le locuteur principal pour ce segment
        speaker_times = {}
        
        for d_start, d_end, d_speaker in diarization:
            # Calculer le chevauchement
            overlap_start = max(d_start, start)
            overlap_end = min(d_end, end)
            
            if overlap_start < overlap_end:
                overlap_duration = overlap_end - overlap_start
                
                if d_speaker in speaker_times:
                    speaker_times[d_speaker] += overlap_duration
                else:
                    speaker_times[d_speaker] = overlap_duration
        
        # Sélectionner le locuteur avec le plus de temps de parole dans ce segment
        if speaker_times:
            speaker = max(speaker_times, key=speaker_times.get)
        
        # Ajouter le segment avec son locuteur
        final_transcription.append({
            "start": start,
            "end": end,
            "speaker": speaker,
            "text": text
        })
    
    return final_transcription

def format_diarized_transcription(
    transcription: List[Dict[str, Any]], 
    include_timestamps: bool = True
) -> str:
    """
    Formate la transcription diarisée en texte lisible
    
    Args:
        transcription: Liste de segments avec texte et locuteur
        include_timestamps: Inclure les horodatages dans la sortie
        
    Returns:
        Texte formaté avec locuteurs
    """
    formatted_text = []
    current_speaker = None
    
    for segment in transcription:
        speaker = segment["speaker"]
        text = segment["text"].strip()
        start = segment["start"]
        end = segment["end"]
        
        # Formater le texte du segment
        if speaker != current_speaker:
            current_speaker = speaker
            if include_timestamps:
                formatted_text.append(f"\n[{format_time(start)}-{format_time(end)}] {speaker}: {text}")
            else:
                formatted_text.append(f"\n{speaker}: {text}")
        else:
            if include_timestamps:
                formatted_text.append(f" [{format_time(start)}-{format_time(end)}] {text}")
            else:
                formatted_text.append(f" {text}")
    
    return "".join(formatted_text).strip()

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