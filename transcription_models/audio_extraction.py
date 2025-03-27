"""
Audio extraction module for video transcription
-----------------------------------------------------
This module provides functions for audio extraction from video files.
"""

import os
import logging
import traceback
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional, Callable, Union

# Logging configuration
logger = logging.getLogger("transcription.audio_extraction")

# Check optional dependencies
try:
    from moviepy.editor import AudioFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    logger.warning("MoviePy not available. Audio conversion will be disabled.")

# Path configuration
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
    Extracts audio from a video and saves it to a file
    
    Args:
        video_path: Path to the video file
        audio_path: Output path for the audio file (optional)
        progress: Progress tracking function (optional)
        audio_format: Audio file format (default: "wav")
        codec: Audio codec to use (default: "pcm_s16le")
        
    Returns:
        Path to the extracted audio file
        
    Raises:
        ImportError: If MoviePy is not available
        Exception: If an error occurs during extraction
    """
    if not MOVIEPY_AVAILABLE:
        raise ImportError("MoviePy is required for audio extraction")
    
    if progress:
        progress(0.1, desc="Extracting audio from video...")
    
    try:
        # Create a temporary file if no path is specified
        if audio_path is None:
            audio_file = NamedTemporaryFile(delete=False, suffix=f".{audio_format}", dir=AUDIO_TMP_DIR)
            audio_path = audio_file.name
            audio_file.close()
        
        # Extract audio
        audio = AudioFileClip(video_path)
        audio.write_audiofile(audio_path, codec=codec, verbose=False, logger=None)
        
        if progress:
            progress(0.3, desc="Audio extraction completed")
        
        return audio_path
        
    except Exception as e:
        error_msg = f"Error during audio extraction: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise Exception(error_msg)

def cleanup_audio_file(audio_path: str) -> bool:
    """
    Deletes a temporary audio file
    
    Args:
        audio_path: Path to the audio file to delete
        
    Returns:
        True if the file was deleted, False otherwise
    """
    if audio_path and isinstance(audio_path, str) and os.path.exists(audio_path):
        # Check if it's a temporary file in our directory
        if audio_path.startswith(str(AUDIO_TMP_DIR)):
            try:
                os.unlink(audio_path)
                return True
            except Exception as e:
                logger.warning(f"Unable to delete temporary audio file: {str(e)}")
    return False

def get_audio_duration(audio_path: str) -> float:
    """
    Gets the duration of an audio file in seconds
    
    Args:
        audio_path: Path to the audio file
        
    Returns:
        Duration in seconds
        
    Raises:
        ImportError: If MoviePy is not available
    """
    if not MOVIEPY_AVAILABLE:
        raise ImportError("MoviePy is required to get audio duration")
    
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        audio.close()
        return duration
    except Exception as e:
        logger.error(f"Error getting audio duration: {str(e)}")
        raise