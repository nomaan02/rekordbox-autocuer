"""
Batch processor for applying calculated cue points to multiple tracks.

This module handles the complete workflow of:
1. Loading the XML tree
2. Calculating cue positions for each track
3. Inserting cues into the XML
4. Exporting the modified XML
"""
from typing import Dict
from rekordbox_parser import (
    parse_rekordbox_xml_advanced,
    parse_rekordbox_xml,
    get_track_element_by_id,
    remove_existing_cues,
    insert_memory_cue,
    insert_hot_cue,
    export_modified_xml
)
from cue_generator import calculate_cue_positions, validate_cue_positions


def process_track_batch(
    xml_path: str,
    track_cue_dict: Dict[str, float],
    remove_existing_memory_cues: bool = True,
    remove_existing_hot_cues: bool = False
) -> str:
    """
    Process a batch of tracks and insert calculated cue points.

    Workflow:
    1. Load XML tree
    2. For each track with a marked drop:
       - Calculate cue positions based on BPM and drop time
       - Remove existing cues (optional)
       - Insert new memory cues and hot cue for drop
    3. Export modified XML to timestamped file

    Args:
        xml_path: Path to the original Rekordbox XML file
        track_cue_dict: Dictionary mapping track_id -> drop_time_ms
                       Example: {'123': 60000.0, '456': 45000.0}
        remove_existing_memory_cues: If True, remove existing memory cues before adding new ones
        remove_existing_hot_cues: If True, also remove existing hot cues

    Returns:
        Path to the exported XML file

    Raises:
        FileNotFoundError: If XML file doesn't exist
        ValueError: If XML parsing fails
        IOError: If XML export fails

    Example:
        >>> track_dict = {'123': 60000.0, '456': 75000.0}
        >>> output_path = process_track_batch('rekordbox.xml', track_dict)
        >>> print(f"Exported to: {output_path}")
    """
    print(f"\n{'=' * 70}")
    print(f"BATCH PROCESSOR: Processing {len(track_cue_dict)} tracks")
    print(f"{'=' * 70}\n")

    # Load XML tree
    print(f"Loading XML: {xml_path}")
    tree = parse_rekordbox_xml_advanced(xml_path)
    xml_data = parse_rekordbox_xml(xml_path)  # Also get parsed data for track info

    tracks_dict = xml_data.get('tracks', {})

    # Statistics
    successful_tracks = 0
    failed_tracks = 0
    total_cues_added = 0
    warnings = []

    # Process each track
    for track_id, drop_time_ms in track_cue_dict.items():
        print(f"\n--- Processing Track ID: {track_id} ---")

        # Get track element from XML
        track_element = get_track_element_by_id(tree, track_id)

        if track_element is None:
            error_msg = f"Track ID {track_id} not found in XML"
            print(f"ERROR: {error_msg}")
            warnings.append(error_msg)
            failed_tracks += 1
            continue

        # Get track info
        track_info = tracks_dict.get(track_id)
        if track_info is None:
            error_msg = f"Track ID {track_id} not in parsed data"
            print(f"ERROR: {error_msg}")
            warnings.append(error_msg)
            failed_tracks += 1
            continue

        track_name = track_info['name']
        artist = track_info['artist']
        bpm = track_info['bpm']
        duration_ms = track_info['duration_ms']

        print(f"Track: {artist} - {track_name}")
        print(f"BPM: {bpm:.1f}, Duration: {duration_ms / 1000:.1f}s")
        print(f"Drop at: {drop_time_ms / 1000:.1f}s")

        # Calculate cue positions
        try:
            cues = calculate_cue_positions(bpm, drop_time_ms, duration_ms)
            print(f"Calculated {len(cues)} cue positions")

            # Validate cues
            is_valid, cue_warnings = validate_cue_positions(cues, duration_ms, bpm)

            if cue_warnings:
                print("Warnings:")
                for warning in cue_warnings:
                    print(f"  - {warning}")
                    warnings.append(f"Track '{track_name}': {warning}")

            if not is_valid:
                error_msg = f"Cue validation failed for track '{track_name}'"
                print(f"ERROR: {error_msg}")
                warnings.append(error_msg)
                failed_tracks += 1
                continue

        except Exception as e:
            error_msg = f"Failed to calculate cues for track '{track_name}': {str(e)}"
            print(f"ERROR: {error_msg}")
            warnings.append(error_msg)
            failed_tracks += 1
            continue

        # Remove existing cues if requested
        if remove_existing_memory_cues or remove_existing_hot_cues:
            removed = remove_existing_cues(
                track_element,
                remove_memory=remove_existing_memory_cues,
                remove_hot=remove_existing_hot_cues
            )
            if removed > 0:
                print(f"Removed {removed} existing cues")

        # Insert new cues
        cues_added = 0
        for cue_time_ms, cue_type, cue_name, color in cues:
            try:
                if cue_type == 'hot':
                    # Insert as hot cue (Drop gets hot cue slot)
                    insert_hot_cue(track_element, cue_time_ms, cue_name, color)
                    print(f"  + Hot Cue: {cue_name} at {cue_time_ms / 1000:.1f}s ({color})")
                else:
                    # Insert as memory cue
                    insert_memory_cue(track_element, cue_time_ms, cue_name, color)
                    print(f"  + Memory Cue: {cue_name} at {cue_time_ms / 1000:.1f}s ({color})")

                cues_added += 1
                total_cues_added += 1

            except Exception as e:
                error_msg = f"Failed to insert cue '{cue_name}' for track '{track_name}': {str(e)}"
                print(f"  ERROR: {error_msg}")
                warnings.append(error_msg)

        if cues_added > 0:
            print(f"Successfully added {cues_added} cues")
            successful_tracks += 1
        else:
            failed_tracks += 1

    # Export modified XML
    print(f"\n{'=' * 70}")
    print("Exporting modified XML...")

    try:
        output_path = export_modified_xml(tree)
        print(f"SUCCESS: Exported to {output_path}")
    except Exception as e:
        error_msg = f"Failed to export XML: {str(e)}"
        print(f"ERROR: {error_msg}")
        raise IOError(error_msg)

    # Summary
    print(f"\n{'=' * 70}")
    print("BATCH PROCESSING SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total tracks processed: {len(track_cue_dict)}")
    print(f"Successful: {successful_tracks}")
    print(f"Failed: {failed_tracks}")
    print(f"Total cues added: {total_cues_added}")

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for warning in warnings[:10]:  # Show first 10 warnings
            print(f"  - {warning}")
        if len(warnings) > 10:
            print(f"  ... and {len(warnings) - 10} more warnings")

    print(f"{'=' * 70}\n")

    return output_path
