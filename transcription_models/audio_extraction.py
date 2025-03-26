"""
Module d'extraction audio pour la transcription vidéo
-----------------------------------------------------
Ce module fournit des fonctions pour l'extraction audio à partir de fichiers vidéo.
"""

import os
import logging
import traceback
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional, Callable, Union

# Configuration du logging
logger = logging.getLogger("transcription.audio_extraction")

# Vérifier les dépendances optionnelles
try:
    from moviepy.editor import AudioFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    logger.warning("MoviePy non disponible. La conversion audio sera désactivée.")

# Configuration des chemins
AUDIO_TMP_DIR = Path("uploads/audio")
AUDIO_TMP_DIR.mkdir(parents=True, exist_ok=True)

def extract_audio(
    video_path: str, 
    audio_path: Optional[str] = None, 
    progress: Optional[Callable] = None,
    audio_format: str = "wav",
    codec: str = "pcm_s16le"
) -> str:
    """
    Extrait l'audio d'une vidéo et le sauvegarde dans un fichier
    
    Args:
        video_path: Chemin vers le fichier vidéo
        audio_path: Chemin de sortie pour le fichier audio (facultatif)
        progress: Fonction de suivi de progression (facultatif)
        audio_format: Format du fichier audio (par défaut: "wav")
        codec: Codec audio à utiliser (par défaut: "pcm_s16le")
        
    Returns:
        Chemin vers le fichier audio extrait
        
    Raises:
        ImportError: Si MoviePy n'est pas disponible
        Exception: Si une erreur survient pendant l'extraction
    """
    if not MOVIEPY_AVAILABLE:
        raise ImportError("MoviePy est requis pour l'extraction audio")
    
    if progress:
        progress(0.1, desc="Extraction de l'audio de la vidéo...")
    
    try:
        # Créer un fichier temporaire si aucun chemin n'est spécifié
        if audio_path is None:
            audio_file = NamedTemporaryFile(delete=False, suffix=f".{audio_format}", dir=AUDIO_TMP_DIR)
            audio_path = audio_file.name
            audio_file.close()
        
        # Extraire l'audio
        audio = AudioFileClip(video_path)
        audio.write_audiofile(audio_path, codec=codec, verbose=False, logger=None)
        
        if progress:
            progress(0.3, desc="Extraction audio terminée")
        
        return audio_path
        
    except Exception as e:
        error_msg = f"Erreur lors de l'extraction audio: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise Exception(error_msg)

def cleanup_audio_file(audio_path: str) -> bool:
    """
    Supprime un fichier audio temporaire
    
    Args:
        audio_path: Chemin vers le fichier audio à supprimer
        
    Returns:
        True si le fichier a été supprimé, False sinon
    """
    if audio_path and isinstance(audio_path, str) and os.path.exists(audio_path):
        # Vérifier si c'est un fichier temporaire dans notre répertoire
        if audio_path.startswith(str(AUDIO_TMP_DIR)):
            try:
                os.unlink(audio_path)
                return True
            except Exception as e:
                logger.warning(f"Impossible de supprimer le fichier audio temporaire: {str(e)}")
    return False

def get_audio_duration(audio_path: str) -> float:
    """
    Obtient la durée d'un fichier audio en secondes
    
    Args:
        audio_path: Chemin vers le fichier audio
        
    Returns:
        Durée en secondes
        
    Raises:
        ImportError: Si MoviePy n'est pas disponible
    """
    if not MOVIEPY_AVAILABLE:
        raise ImportError("MoviePy est requis pour obtenir la durée audio")
    
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        audio.close()
        return duration
    except Exception as e:
        logger.error(f"Erreur lors de l'obtention de la durée audio: {str(e)}")
        raise