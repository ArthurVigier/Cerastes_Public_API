"""
Speaker diarization module for video transcription
------------------------------------------------
This module provides functions for speaker identification (diarization)
in audio files and for attributing speakers to transcription segments.
"""

import os
import logging
import traceback
from typing import List, Dict, Tuple, Optional, Callable, Any, Union

# Logging configuration
logger = logging.getLogger("transcription.diarization")

# Check optional dependencies
try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False
    logger.warning("Pyannote.audio not available. Diarization will be disabled.")

# Configuration
HUGGINGFACE_TOKEN = os.environ.get("HUGGINGFACE_TOKEN", "")
DIARIZATION_MODEL = "pyannote/speaker-diarization-3.1"

# Global variable for the model
diarization_pipeline = None

def load_diarization_model(huggingface_token: Optional[str] = None):
    """
    Loads the diarization model
    
    Args:
        huggingface_token: Hugging Face token for model access
        
    Returns:
        Diarization pipeline
        
    Raises:
        ImportError: If pyannote.audio is not available
        ValueError: If no token is provided
    """
    global diarization_pipeline
    
    if not PYANNOTE_AVAILABLE:
        raise ImportError("Pyannote.audio is required for diarization")
    
    token = huggingface_token or HUGGINGFACE_TOKEN
    if not token:
        raise ValueError("A Hugging Face token is required for diarization")
    
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
    Identifies speakers in an audio file
    
    Args:
        audio_path: Path to the audio file
        huggingface_token: Hugging Face token for model access
        progress: Progress tracking function (optional)
        
    Returns:
        List of segments with speaker information (start, end, speaker)
        
    Raises:
        ImportError: If pyannote.audio is not available
        ValueError: If no token is provided
        Exception: If an error occurs during diarization
    """
    try:
        if progress:
            progress(0.6, desc="Loading diarization model...")
        
        # Initialize diarization pipeline
        pipeline = load_diarization_model(huggingface_token)
        
        if progress:
            progress(0.7, desc="Speaker identification in progress...")
        
        # Perform diarization
        diarization = pipeline(audio_path)
        
        # Extract segments with speakers
        speaker_segments = []
        for segment, _, speaker in diarization.itertracks(yield_label=True):
            speaker_segments.append((segment.start, segment.end, speaker))
        
        if progress:
            progress(0.9, desc="Speaker identification completed")
        
        return speaker_segments
        
    except Exception as e:
        error_msg = f"Error during diarization: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise Exception(error_msg)

def assign_speakers(
    transcription: Dict[str, Any], 
    diarization: List[Tuple[float, float, str]]
) -> List[Dict[str, Any]]:
    """
    Associates identified speakers with transcription segments
    
    Args:
        transcription: Transcription result from Whisper
        diarization: Diarization result from Pyannote
        
    Returns:
        List of segments with text and assigned speaker
    """
    final_transcription = []
    
    segments = transcription["segments"]
    
    for segment in segments:
        start, end, text = segment["start"], segment["end"], segment["text"]
        speaker = "Unknown"
        
        # Find the main speaker for this segment
        speaker_times = {}
        
        for d_start, d_end, d_speaker in diarization:
            # Calculate overlap
            overlap_start = max(d_start, start)
            overlap_end = min(d_end, end)
            
            if overlap_start < overlap_end:
                overlap_duration = overlap_end - overlap_start
                
                if d_speaker in speaker_times:
                    speaker_times[d_speaker] += overlap_duration
                else:
                    speaker_times[d_speaker] = overlap_duration
        
        # Select the speaker with the most speaking time in this segment
        if speaker_times:
            speaker = max(speaker_times, key=speaker_times.get)
        
        # Add the segment with its speaker
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
    Formats the diarized transcription into readable text
    
    Args:
        transcription: List of segments with text and speaker
        include_timestamps: Include timestamps in the output
        
    Returns:
        Formatted text with speakers
    """
    formatted_text = []
    current_speaker = None
    
    for segment in transcription:
        speaker = segment["speaker"]
        text = segment["text"].strip()
        start = segment["start"]
        end = segment["end"]
        
        # Format the segment text
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
    Formats seconds into hh:mm:ss format
    
    Args:
        seconds: Number of seconds
        
    Returns:
        Formatted string
    """
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"