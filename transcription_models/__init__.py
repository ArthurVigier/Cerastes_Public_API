"""
Package de modèles de transcription
----------------------------------
Ce package contient tous les modules nécessaires pour la transcription
de fichiers audio et vidéo, avec ou sans identification de locuteurs.
"""

# Exposer les fonctions principales
from .transcription_core import (
    process_monologue,
    process_multiple_speakers,
    transcribe_external_audio,
    get_available_models
)

# Exposer des fonctions utilitaires spécifiques qui peuvent être utiles ailleurs
from .audio_extraction import extract_audio, cleanup_audio_file
from .whisper_utils import cleanup_whisper_model
from .diarization import format_diarized_transcription

__all__ = [
    'process_monologue',
    'process_multiple_speakers',
    'transcribe_external_audio',
    'get_available_models',
    'extract_audio',
    'cleanup_audio_file',
    'cleanup_whisper_model',
    'format_diarized_transcription'
]