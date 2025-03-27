"""
Utilitaires de transcription vidéo pour l'API
--------------------------------------------
Ce module fournit des fonctions pour la transcription audio de vidéos,
avec et sans identification des locuteurs (diarization).
"""

import os
import logging
import whisper
import numpy as np
import traceback
from tempfile import NamedTemporaryFile
from pathlib import Path

# Logging
logger = logging.getLogger("transcription_utils")

# Vérifier les dépendances optionnelles
try:
    from moviepy.editor import AudioFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    logger.warning("MoviePy non disponible. La conversion audio sera désactivée.")

try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False
    logger.warning("Pyannote.audio non disponible. La diarization sera désactivée.")

# Modèle Whisper global pour réutilisation
whisper_model = None

# Configuration
HUGGINGFACE_TOKEN = os.environ.get("HUGGINGFACE_TOKEN", "")
WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "medium")
AUDIO_TMP_DIR = Path("uploads/audio")
AUDIO_TMP_DIR.mkdir(parents=True, exist_ok=True)

def get_whisper_model(model_size=None):
    """Charge ou récupère le modèle Whisper"""
    global whisper_model
    
    if whisper_model is None:
        model_size = model_size or WHISPER_MODEL_SIZE
        logger.info(f"Chargement du modèle Whisper {model_size}...")
        whisper_model = whisper.load_model(model_size)
        
    return whisper_model

def extract_audio(video_path, audio_path=None, progress=None):
    """
    Extrait l'audio d'une vidéo
    
    Args:
        video_path: Chemin vers le fichier vidéo
        audio_path: Chemin de sortie pour le fichier audio (facultatif)
        progress: Fonction de suivi de progression (facultatif)
        
    Returns:
        Chemin vers le fichier audio extrait
    """
    if not MOVIEPY_AVAILABLE:
        raise ImportError("MoviePy est requis pour l'extraction audio")
    
    if progress:
        progress(0.1, desc="Extraction de l'audio de la vidéo...")
    
    try:
        # Créer un fichier temporaire si aucun chemin n'est spécifié
        if audio_path is None:
            audio_file = NamedTemporaryFile(delete=False, suffix=".wav", dir=AUDIO_TMP_DIR)
            audio_path = audio_file.name
            audio_file.close()
        
        # Extraire l'audio
        audio = AudioFileClip(video_path)
        audio.write_audiofile(audio_path, codec="pcm_s16le", verbose=False, logger=None)
        
        if progress:
            progress(0.3, desc="Extraction audio terminée")
        
        return audio_path
        
    except Exception as e:
        error_msg = f"Erreur lors de l'extraction audio: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise Exception(error_msg)

def transcribe_audio(audio_path, model_size=None, progress=None):
    """
    Transcrit un fichier audio en texte
    
    Args:
        audio_path: Chemin vers le fichier audio
        model_size: Taille du modèle Whisper à utiliser
        progress: Fonction de suivi de progression (facultatif)
        
    Returns:
        Texte transcrit ou segments détaillés selon le paramètre detailed
    """
    try:
        if progress:
            progress(0.4, desc="Chargement du modèle de transcription...")
        
        # Charger le modèle Whisper
        model = get_whisper_model(model_size)
        
        if progress:
            progress(0.5, desc="Transcription audio en cours...")
        
        # Transcrire l'audio
        result = model.transcribe(audio_path)
        
        if progress:
            progress(0.8, desc="Transcription terminée")
        
        return result
        
    except Exception as e:
        error_msg = f"Erreur lors de la transcription: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise Exception(error_msg)

def diarize_audio(audio_path, huggingface_token=None, progress=None):
    """
    Identifie les locuteurs dans un fichier audio
    
    Args:
        audio_path: Chemin vers le fichier audio
        huggingface_token: Token Hugging Face pour l'accès au modèle
        progress: Fonction de suivi de progression (facultatif)
        
    Returns:
        Liste de segments avec informations sur les locuteurs
    """
    if not PYANNOTE_AVAILABLE:
        raise ImportError("Pyannote.audio est requis pour la diarization")
    
    if not huggingface_token and not HUGGINGFACE_TOKEN:
        raise ValueError("Un token Hugging Face est requis pour la diarization")
    
    token = huggingface_token or HUGGINGFACE_TOKEN
    
    try:
        if progress:
            progress(0.6, desc="Chargement du modèle de diarization...")
        
        # Initialiser le pipeline de diarization
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=token
        )
        
        if progress:
            progress(0.7, desc="Identification des locuteurs en cours...")
        
        # Effectuer la diarization
        diarization = pipeline(audio_path)
        
        # Extraire les segments avec locuteurs
        speaker_segments = []
        for segment, _, speaker in diarization.itertracks(yield_label=True):
            speaker_segments.append((segment.start, segment.end, speaker))
        
        if progress:
            progress(0.9, desc="Identification des locuteurs terminée")
        
        return speaker_segments
        
    except Exception as e:
        error_msg = f"Erreur lors de la diarization: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise Exception(error_msg)

def assign_speakers(transcription, diarization):
    """
    Associe les locuteurs identifiés aux segments de transcription
    
    Args:
        transcription: Résultat de la transcription avec Whisper
        diarization: Résultat de la diarization avec Pyannote
        
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

def process_monologue(video_path, output_txt=None, model_size=None, progress=None):
    """
    Transcrit une vidéo sans identification des locuteurs
    
    Args:
        video_path: Chemin vers le fichier vidéo
        output_txt: Chemin de sortie pour le fichier texte (facultatif)
        model_size: Taille du modèle Whisper à utiliser
        progress: Fonction de suivi de progression (facultatif)
        
    Returns:
        Texte transcrit et chemin vers le fichier texte s'il a été créé
    """
    try:
        # Extraire l'audio
        audio_path = extract_audio(video_path, progress=progress)
        
        # Transcrire l'audio
        result = transcribe_audio(audio_path, model_size, progress=progress)
        transcription = result["text"]
        
        # Enregistrer le résultat si un chemin est spécifié
        if output_txt:
            with open(output_txt, "w", encoding="utf-8") as f:
                f.write(transcription)
            
            if progress:
                progress(1.0, desc=f"Transcription enregistrée dans {output_txt}")
        else:
            if progress:
                progress(1.0, desc="Transcription terminée")
        
        # Nettoyer le fichier audio temporaire
        if audio_path.startswith(str(AUDIO_TMP_DIR)):
            try:
                os.unlink(audio_path)
            except:
                pass
        
        return {
            "transcription": transcription,
            "segments": result["segments"],
            "file_path": output_txt
        }
        
    except Exception as e:
        error_msg = f"Erreur lors du traitement vidéo (monologue): {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise Exception(error_msg)

def process_multiple_speakers(video_path, output_txt=None, model_size=None, huggingface_token=None, progress=None):
    """
    Transcrit une vidéo avec identification des locuteurs
    
    Args:
        video_path: Chemin vers le fichier vidéo
        output_txt: Chemin de sortie pour le fichier texte (facultatif)
        model_size: Taille du modèle Whisper à utiliser
        huggingface_token: Token Hugging Face pour l'accès au modèle
        progress: Fonction de suivi de progression (facultatif)
        
    Returns:
        Liste de segments avec texte et locuteur, et chemin vers le fichier texte s'il a été créé
    """
    try:
        # Extraire l'audio
        audio_path = extract_audio(video_path, progress=progress)
        
        # Transcrire l'audio
        result = transcribe_audio(audio_path, model_size, progress=progress)
        
        # Identifier les locuteurs
        diarization = diarize_audio(audio_path, huggingface_token, progress=progress)
        
        # Associer les locuteurs à la transcription
        final_transcription = assign_speakers(result, diarization)
        
        # Enregistrer le résultat si un chemin est spécifié
        if output_txt:
            with open(output_txt, "w", encoding="utf-8") as f:
                for segment in final_transcription:
                    f.write(f"[{segment['start']:.2f} - {segment['end']:.2f}] {segment['speaker']}: {segment['text']}\n")
            
            if progress:
                progress(1.0, desc=f"Transcription enregistrée dans {output_txt}")
        else:
            if progress:
                progress(1.0, desc="Transcription terminée")
        
        # Nettoyer le fichier audio temporaire
        if audio_path.startswith(str(AUDIO_TMP_DIR)):
            try:
                os.unlink(audio_path)
            except:
                pass
        
        return {
            "segments": final_transcription,
            "file_path": output_txt
        }
        
    except Exception as e:
        error_msg = f"Erreur lors du traitement vidéo (locuteurs multiples): {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise Exception(error_msg)