import os
import logging
import traceback
from typing import List, Dict, Tuple, Optional, Callable, Any

from resemblyzer import VoiceEncoder, preprocess_wav
from resemblyzer.hparams import sampling_rate
from pydub import AudioSegment
import numpy as np
from sklearn.cluster import KMeans

# Logging configuration
logger = logging.getLogger("transcription.diarization")

def diarize_audio(
    audio_path: str,
    progress: Optional[Callable] = None,
    num_speakers: Optional[int] = None
) -> List[Tuple[float, float, str]]:
    """
    Simple speaker diarization using speaker embeddings and clustering.

    Args:
        audio_path: Path to the audio file
        progress: Progress callback (optional)
        num_speakers: Expected number of speakers. If None, estimated (WIP)

    Returns:
        List of segments (start_time, end_time, speaker_label)
    """
    try:
        if progress:
            progress(0.2, desc="Loading and preprocessing audio...")

        wav = preprocess_wav(audio_path)

        if progress:
            progress(0.4, desc="Generating embeddings...")

        encoder = VoiceEncoder()
        _, cont_embeds, wav_splits = encoder.embed_utterance(wav, return_partials=True)

        if progress:
            progress(0.6, desc="Clustering voices...")

        X = np.array(cont_embeds)
        if num_speakers is None:
            num_speakers = 2  # default, or use heuristic

        kmeans = KMeans(n_clusters=num_speakers, random_state=0)
        labels = kmeans.fit_predict(X)

        if progress:
            progress(0.8, desc="Building diarization result...")

        speaker_segments = []
        for (s, e), label in zip(wav_splits, labels):
            speaker_segments.append((s, e, f"Speaker_{label}"))

        return speaker_segments

    except Exception as e:
        error_msg = f"Error during diarization: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise Exception(error_msg)
