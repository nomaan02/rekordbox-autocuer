"""
Cue point calculation engine for Rekordbox Autocuer.

This module handles all BPM-based calculations for generating hot cues and memory
cues around a user-marked drop point.
"""
from typing import List, Tuple


def calculate_cue_positions(
    bpm: float,
    drop_time_ms: float,
    track_duration_ms: float,
    time_signature: str = "4/4"
) -> List[Tuple[float, str, str, str]]:
    """
    Calculate cue point positions based on BPM and drop time.

    This function generates a series of hot cues and memory cues positioned at
    musically-relevant intervals around the drop point. The intervals are based
    on bar durations calculated from the track's BPM.

    BPM Calculation Logic:
    ----------------------
    1. Beat duration (ms) = 60000 / BPM
       - At 120 BPM: 60000 / 120 = 500ms per beat

    2. Bar duration (ms) = Beat duration * beats_per_bar
       - For 4/4 time: Beat duration * 4
       - At 120 BPM: 500ms * 4 = 2000ms per bar

    3. Multi-bar phrases = Bar duration * num_bars
       - 16 bars at 120 BPM: 2000ms * 16 = 32000ms (32 seconds)
       - 32 bars at 120 BPM: 2000ms * 32 = 64000ms (64 seconds)

    Cue Point Layout:
    -----------------
    Generated cues (in order of appearance):
    - Drop - 32 bars: "Intro/Build" (memory, orange)
    - Drop - 16 bars: "Pre-Drop" (memory, yellow)
    - Drop: "Drop" (hot, red)
    - Drop + 16 bars: "Post-Drop" (memory, blue)
    - Drop + 32 bars: "Outro/Break" (memory, aqua)

    Args:
        bpm: Track tempo in beats per minute (must be > 0)
        drop_time_ms: Time of the drop in milliseconds (user-marked position)
        track_duration_ms: Total track duration in milliseconds
        time_signature: Time signature as string (default "4/4")

    Returns:
        List of tuples (time_ms, cue_type, cue_name, color) sorted by time.
        Only includes cues that fall within [0, track_duration_ms].

    Example:
        >>> # 120 BPM track, drop at 60 seconds
        >>> cues = calculate_cue_positions(120.0, 60000.0, 180000.0)
        >>> # Returns cues at 28s, 44s, 60s, 76s, 92s
    """
    if bpm <= 0:
        raise ValueError(f"BPM must be positive, got {bpm}")
    if drop_time_ms < 0:
        raise ValueError(f"Drop time cannot be negative, got {drop_time_ms}")
    if track_duration_ms <= 0:
        raise ValueError(f"Track duration must be positive, got {track_duration_ms}")

    # Parse time signature
    beats_per_bar = 4  # Default for 4/4
    if "/" in time_signature:
        try:
            beats_per_bar = int(time_signature.split("/")[0])
        except (ValueError, IndexError):
            beats_per_bar = 4

    # Calculate bar duration in milliseconds
    # Beat duration = 60000ms / BPM
    # Bar duration = Beat duration * beats_per_bar
    beat_duration_ms = 60000.0 / bpm
    bar_duration_ms = beat_duration_ms * beats_per_bar

    # Define cue positions relative to drop
    # Format: (bars_offset, cue_name, cue_type, color)
    cue_definitions = [
        (-32, "-32 bars", "memory", "orange"),   # 32 bars before drop
        (-16, "-16 bars", "memory", "yellow"),   # 16 bars before drop
        (0, "Drop", "hot", "red"),               # The drop itself
        (16, "+16 bars", "memory", "blue"),      # 16 bars after drop
        (32, "+32 bars", "memory", "aqua"),      # 32 bars after drop
    ]

    cues = []

    for bar_offset, cue_name, cue_type, color in cue_definitions:
        # Calculate absolute time position
        time_ms = drop_time_ms + (bar_offset * bar_duration_ms)

        # Only include cues within valid track bounds
        if 0 <= time_ms <= track_duration_ms:
            cues.append((time_ms, cue_type, cue_name, color))

    # Sort by time (should already be sorted, but ensure it)
    cues.sort(key=lambda x: x[0])

    return cues


def snap_to_grid(time_ms: float, bpm: float, grid_resolution: int = 4) -> float:
    """
    Snap a time position to the nearest beat grid position.

    This function quantizes a time value to align with musical beats, which is
    useful for ensuring cue points land exactly on beat boundaries rather than
    slightly off-time.

    Args:
        time_ms: Time position in milliseconds to snap
        bpm: Track tempo in beats per minute
        grid_resolution: Grid divisions (4 = quarter notes, 8 = eighth notes, etc.)
                        Higher values = finer grid, lower values = coarser grid

    Returns:
        Snapped time position in milliseconds

    Example:
        >>> # At 120 BPM, beats are 500ms apart
        >>> snap_to_grid(1230.0, 120.0, 4)  # Snap to quarter notes
        1000.0  # Snapped to 2nd beat

        >>> snap_to_grid(1750.0, 120.0, 4)
        2000.0  # Snapped to 4th beat
    """
    if bpm <= 0:
        raise ValueError(f"BPM must be positive, got {bpm}")
    if grid_resolution <= 0:
        raise ValueError(f"Grid resolution must be positive, got {grid_resolution}")

    # Calculate grid interval
    beat_duration_ms = 60000.0 / bpm
    grid_interval_ms = beat_duration_ms / (grid_resolution / 4)

    # Snap to nearest grid position
    num_intervals = round(time_ms / grid_interval_ms)
    snapped_time = num_intervals * grid_interval_ms

    return snapped_time


def validate_cue_positions(
    cues: List[Tuple[float, str, str, str]],
    track_duration_ms: float,
    bpm: float
) -> Tuple[bool, List[str]]:
    """
    Validate cue positions and return warnings for potential issues.

    Performs sanity checks on generated cue points to ensure they are:
    - Within valid time bounds
    - Properly spaced
    - Not overlapping
    - Reasonable given the track length and BPM

    Args:
        cues: List of cue tuples (time_ms, cue_type, cue_name, color)
        track_duration_ms: Total track duration in milliseconds
        bpm: Track tempo in beats per minute

    Returns:
        Tuple of (is_valid: bool, warnings: list of warning strings)
        - is_valid: True if no critical errors, False otherwise
        - warnings: List of warning messages (empty if no issues)

    Example:
        >>> cues = [(1000.0, 'memory', 'Cue1', 'red'), (2000.0, 'hot', 'Cue2', 'blue')]
        >>> is_valid, warnings = validate_cue_positions(cues, 180000.0, 120.0)
        >>> print(is_valid)  # True if cues are reasonable
    """
    warnings = []
    is_valid = True

    # Minimum spacing between cues (1 second)
    MIN_CUE_SPACING_MS = 1000.0

    # Check for empty cue list
    if not cues:
        warnings.append("No cues generated")
        return True, warnings  # Not an error, just a note

    # Check each cue's time bounds
    for i, (time_ms, cue_type, cue_name, color) in enumerate(cues):
        # Check if cue is before track start
        if time_ms < 0:
            warnings.append(f"Cue '{cue_name}' at {format_cue_time(time_ms)} is before track start")
            is_valid = False

        # Check if cue is after track end
        if time_ms > track_duration_ms:
            warnings.append(f"Cue '{cue_name}' at {format_cue_time(time_ms)} is after track end")
            is_valid = False

    # Check for overlapping or too-close cues
    sorted_cues = sorted(cues, key=lambda x: x[0])
    for i in range(len(sorted_cues) - 1):
        time1 = sorted_cues[i][0]
        time2 = sorted_cues[i + 1][0]
        name1 = sorted_cues[i][2]
        name2 = sorted_cues[i + 1][2]

        spacing = time2 - time1

        if spacing < MIN_CUE_SPACING_MS:
            warnings.append(
                f"Cues '{name1}' and '{name2}' are too close together "
                f"({spacing:.0f}ms apart, minimum {MIN_CUE_SPACING_MS:.0f}ms recommended)"
            )

    # Check if track is too short for standard cue pattern
    beat_duration_ms = 60000.0 / bpm
    bar_duration_ms = beat_duration_ms * 4
    standard_cue_range = bar_duration_ms * 64  # 32 bars before + 32 bars after

    if track_duration_ms < standard_cue_range:
        warnings.append(
            f"Track may be too short for full cue pattern. "
            f"Standard pattern needs ~{standard_cue_range / 1000:.0f}s, "
            f"track is {track_duration_ms / 1000:.0f}s"
        )

    # Check if BPM is reasonable (typical EDM range: 100-180 BPM)
    if bpm < 60 or bpm > 200:
        warnings.append(
            f"BPM ({bpm:.1f}) is outside typical range (60-200). "
            f"Verify BPM is correct."
        )

    return is_valid, warnings


def format_cue_time(time_ms: float) -> str:
    """
    Format a time value in milliseconds to mm:ss display format.

    Args:
        time_ms: Time in milliseconds

    Returns:
        String in "mm:ss" format

    Example:
        >>> format_cue_time(65000.0)
        '01:05'

        >>> format_cue_time(3500.0)
        '00:03'

        >>> format_cue_time(125000.0)
        '02:05'
    """
    total_seconds = int(time_ms / 1000)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"
