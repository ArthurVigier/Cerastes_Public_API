"""
Whisper usage module for audio transcription
----------------------------------------------------------
This module provides functions for audio transcription with the Whisper model.
"""

import os
import gc
import logging
import traceback
from typing import Dict, Any, Optional, Callable, Union

# Logging
logger = logging.getLogger("transcription.whisper")

# Check dependencies
try:
    import whisper
    import torch
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("Whisper is not available. Transcription will be disabled.")

# Global model for reuse
whisper_model = None
current_model_size = None

# Configuration
WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "medium")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def get_whisper_model(model_size: Optional[str] = None) -> Any:
    """
    Loads or retrieves the Whisper model
    
    Args:
        model_size: Size of the Whisper model to use ('tiny', 'base', 'small', 'medium', 'large')
        
    Returns:
        Whisper model instance
        
    Raises:
        ImportError: If Whisper is not available
    """
    global whisper_model, current_model_size
    
    if not WHISPER_AVAILABLE:
        raise ImportError("Whisper is required for transcription")
    
    # Define model size
    selected_size = model_size or WHISPER_MODEL_SIZE
    
    # Check if we need to load a new model
    if whisper_model is None or current_model_size != selected_size:
        # Free memory if a model was already loaded
        if whisper_model is not None:
            del whisper_model
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        
        logger.info(f"Loading Whisper model {selected_size}...")
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
    Transcribes an audio file to text
    
    Args:
        audio_path: Path to the audio file
        model_size: Size of the Whisper model to use
        language: Language code for transcription (e.g., 'fr', 'en')
        progress: Progress tracking function (optional)
        whisper_options: Additional options to pass to Whisper
        
    Returns:
        Dictionary containing the transcription results
        
    Raises:
        ImportError: If Whisper is not available
        Exception: If an error occurs during transcription
    """
    try:
        if progress:
            progress(0.4, desc="Loading transcription model...")
        
        # Load the Whisper model
        model = get_whisper_model(model_size)
        
        if progress:
            progress(0.5, desc="Audio transcription in progress...")
        
        # Prepare transcription options
        options = {
            "fp16": torch.cuda.is_available(),
            "verbose": False
        }
        
        # Add language if specified
        if language:
            options["language"] = language
            
        # Add additional options
        options.update(whisper_options)
        
        # Transcribe the audio
        result = model.transcribe(audio_path, **options)
        
        if progress:
            progress(0.8, desc="Transcription completed")
        
        return result
        
    except Exception as e:
        error_msg = f"Error during transcription: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise Exception(error_msg)

def cleanup_whisper_model() -> bool:
    """
    Frees the Whisper model memory
    
    Returns:
        True if the model was freed, False otherwise
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
            logger.error(f"Error when freeing the Whisper model: {str(e)}")
            
    return False

def get_available_whisper_models() -> Dict[str, Dict[str, Any]]:
    """
    Returns available Whisper models with their characteristics
    
    Returns:
        Dictionary of available models
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
    Formats the Whisper result into readable text
    
    Args:
        result: Whisper transcription result
        include_timestamps: Include timestamps in the output
        
    Returns:
        Formatted text
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
    Formats seconds into hh:mm:ss format
    
    Args:
        seconds: Number of seconds
        
    Returns:
        Formatted string
    """
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"