"""
Main module for video and audio transcription
----------------------------------------------------------------
This module integrates the functionalities of other transcription modules
to provide a unified API for transcribing multimedia content.
"""

import os
import json
import logging
import time
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
from tempfile import NamedTemporaryFile

# Import specialized modules
from .audio_extraction import extract_audio, cleanup_audio_file
from .whisper_utils import transcribe_audio, format_whisper_result, cleanup_whisper_model
from .diarization import diarize_audio, assign_speakers, format_diarized_transcription

# Logging configuration
logger = logging.getLogger("transcription.core")

# Temporary directory for output files
RESULTS_DIR = Path("results/transcriptions")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def process_monologue(
    video_path: str, 
    output_txt: Optional[str] = None, 
    model_size: Optional[str] = None, 
    progress: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Transcribes a video in monologue mode (without speaker identification)
    
    Args:
        video_path: Path to the video file
        output_txt: Output path for the text file (optional)
        model_size: Size of the Whisper model to use
        progress: Progress tracking function (optional)
        
    Returns:
        Dictionary containing the complete transcription and segments
        
    Raises:
        Exception: If an error occurs during processing
    """
    try:
        # Extract audio
        if progress:
            progress(0.1, desc="Extracting audio...")
        
        audio_path = extract_audio(video_path, progress=progress)
        audio_extracted = True
        
        # Transcribe audio
        if progress:
            progress(0.3, desc="Transcription in progress...")
        
        result = transcribe_audio(audio_path, model_size, progress=progress)
        
        # Save transcription if requested
        if output_txt:
            with open(output_txt, "w", encoding="utf-8") as f:
                formatted_text = format_whisper_result(result)
                f.write(formatted_text)
            
            if progress:
                progress(0.95, desc=f"Transcription saved to {output_txt}")
        
        # Cleanup
        if progress:
            progress(1.0, desc="Transcription completed")
        
        if audio_extracted:
            cleanup_audio_file(audio_path)
        
        # Unified output format
        return {
            "transcription": result["text"],
            "segments": result["segments"],
            "language": result.get("language", ""),
            "duration": result.get("duration", 0)
        }
        
    except Exception as e:
        error_msg = f"Error during transcription: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        # Cleanup in case of error
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
    Transcribes a video with speaker identification
    
    Args:
        video_path: Path to the video file
        output_txt: Output path for the text file (optional)
        model_size: Size of the Whisper model to use
        huggingface_token: Hugging Face token for access to the diarization model
        progress: Progress tracking function (optional)
        
    Returns:
        Dictionary containing the transcription with speaker identification
        
    Raises:
        Exception: If an error occurs during processing
    """
    try:
        # Extract audio
        if progress:
            progress(0.1, desc="Extracting audio...")
        
        audio_path = extract_audio(video_path, progress=progress)
        audio_extracted = True
        
        # Transcribe audio
        if progress:
            progress(0.3, desc="Transcription in progress...")
        
        result = transcribe_audio(audio_path, model_size, progress=progress)
        
        # Identify speakers
        if progress:
            progress(0.5, desc="Speaker identification in progress...")
        
        diarization = diarize_audio(audio_path, huggingface_token, progress=progress)
        
        # Associate speakers with the transcription
        final_transcription = assign_speakers(result, diarization)
        
        # Save the result if requested
        if output_txt:
            with open(output_txt, "w", encoding="utf-8") as f:
                formatted_text = format_diarized_transcription(final_transcription)
                f.write(formatted_text)
            
            if progress:
                progress(0.95, desc=f"Transcription saved to {output_txt}")
        
        # Cleanup
        if progress:
            progress(1.0, desc="Transcription completed")
        
        if audio_extracted:
            cleanup_audio_file(audio_path)
        
        # Unified output format
        return {
            "transcription": format_diarized_transcription(final_transcription, include_timestamps=False),
            "segments": final_transcription,
            "language": result.get("language", ""),
            "duration": result.get("duration", 0),
            "speakers": list(set(segment["speaker"] for segment in final_transcription))
        }
        
    except Exception as e:
        error_msg = f"Error during transcription with speaker identification: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        # Cleanup in case of error
        if 'audio_path' in locals() and 'audio_extracted' in locals() and audio_extracted:
            cleanup_audio_file(audio_path)
        
        # Free model memory
        cleanup_whisper_model()
        
        raise Exception(error_msg)

def transcribe_external_audio(
    audio_path: str,
    model_size: Optional[str] = None,
    output_txt: Optional[str] = None,
    progress: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Transcribes an existing audio file without extraction
    
    Args:
        audio_path: Path to the audio file
        model_size: Size of the Whisper model to use
        output_txt: Output path for the text file (optional)
        progress: Progress tracking function (optional)
        
    Returns:
        Dictionary containing the complete transcription and segments
        
    Raises:
        Exception: If an error occurs during processing
    """
    try:
        # Transcribe audio
        if progress:
            progress(0.2, desc="Audio transcription in progress...")
        
        result = transcribe_audio(audio_path, model_size, progress=progress)
        
        # Save transcription if requested
        if output_txt:
            with open(output_txt, "w", encoding="utf-8") as f:
                formatted_text = format_whisper_result(result)
                f.write(formatted_text)
            
            if progress:
                progress(0.9, desc=f"Transcription saved to {output_txt}")
        
        if progress:
            progress(1.0, desc="Transcription completed")
        
        # Unified output format
        return {
            "transcription": result["text"],
            "segments": result["segments"],
            "language": result.get("language", ""),
            "duration": result.get("duration", 0)
        }
        
    except Exception as e:
        error_msg = f"Error during audio transcription: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise Exception(error_msg)

def get_available_models() -> Dict[str, Dict[str, Any]]:
    """
    Returns information about available transcription models
    
    Returns:
        Dictionary with information about the models
    """
    from .whisper_utils import get_available_whisper_models
    
    models = {
        "whisper": get_available_whisper_models(),
        "diarization": {
            "pyannote": {
                "description": "Diarization model for speaker identification",
                "requires_token": True,
                "source": "https://huggingface.co/pyannote/speaker-diarization-3.1"
            }
        }
    }
    
    return models

# Ajoutez cette fonction à la fin du fichier
def analyze_transcript(transcription: str, language: Optional[str] = None) -> str:
    """
    Analyze a transcription text to extract key points and insights
    
    Args:
        transcription: Text transcription to analyze
        language: Language of the transcription
        
    Returns:
        Analysis text
    """
    from model_manager import ModelManager
    
    try:
        # Get LLM model
        model = ModelManager.get_instance().get_model("llm")
        if not model:
            return "Error: No LLM model available for analysis"
        
        # Generate analysis
        result = model.generate(transcription, max_tokens=1024)
        return result
    except Exception as e:
        logger.error(f"Error during transcription analysis: {str(e)}")
        logger.error(traceback.format_exc())
        return f"Error analyzing transcription: {str(e)}"