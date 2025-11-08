"""
Audio processing utilities for analyzing tracks and generating waveforms.
"""
import librosa
import numpy as np
from typing import Tuple, List


def load_audio_file(file_path: str) -> Tuple[np.ndarray, int]:
    """
    Load an audio file using librosa.

    Args:
        file_path: Path to the audio file

    Returns:
        Tuple of (audio_data, sample_rate)
        - audio_data: NumPy array of audio samples
        - sample_rate: Sample rate in Hz
    """
    try:
        # Load audio file with librosa
        # sr=None preserves the native sample rate
        audio_data, sample_rate = librosa.load(file_path, sr=None, mono=True)
        return audio_data, sample_rate
    except Exception as e:
        raise ValueError(f"Failed to load audio file '{file_path}': {str(e)}")


def generate_waveform_data(audio_data: np.ndarray, sample_rate: int, bins: int = 1024) -> List[float]:
    """
    Generate waveform data for visualization.

    Args:
        audio_data: Audio samples as NumPy array
        sample_rate: Sample rate in Hz
        bins: Number of bins/points to generate for the waveform

    Returns:
        List of amplitude values representing the waveform envelope
    """
    if len(audio_data) == 0:
        return []

    # Calculate samples per bin
    samples_per_bin = len(audio_data) // bins

    if samples_per_bin == 0:
        # Audio is shorter than requested bins, return actual values
        return audio_data.tolist()

    waveform = []

    for i in range(bins):
        start_idx = i * samples_per_bin
        end_idx = start_idx + samples_per_bin

        # Handle last bin to include any remaining samples
        if i == bins - 1:
            end_idx = len(audio_data)

        # Get the chunk and calculate RMS amplitude
        chunk = audio_data[start_idx:end_idx]

        if len(chunk) > 0:
            # Calculate RMS (root mean square) for the chunk
            rms = np.sqrt(np.mean(chunk ** 2))
            waveform.append(float(rms))
        else:
            waveform.append(0.0)

    return waveform
