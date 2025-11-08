"""
Rekordbox XML parser for extracting playlist and track information.
Also handles XML modification to insert calculated cue points.
"""
from lxml import etree
from typing import Dict, List, Optional
import os
from datetime import datetime


def parse_rekordbox_xml(file_path: str) -> dict:
    """
    Parse a Rekordbox XML export file.

    Args:
        file_path: Path to the Rekordbox XML file

    Returns:
        Dictionary with keys 'playlists' and 'tracks'
        - playlists: List of playlist dictionaries with 'name' and 'track_ids'
        - tracks: Dictionary mapping track_id to track data
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"XML file not found: {file_path}")

    try:
        tree = etree.parse(file_path)
        root = tree.getroot()
    except Exception as e:
        raise ValueError(f"Failed to parse XML file: {str(e)}")

    # Parse tracks from COLLECTION element
    tracks = {}
    collection = root.find('.//COLLECTION')

    if collection is not None:
        for track in collection.findall('TRACK'):
            track_id = track.get('TrackID')
            if track_id:
                # Extract cue points
                cue_points = []
                for position_mark in track.findall('.//POSITION_MARK'):
                    cue_type = position_mark.get('Type')
                    if cue_type == '0':  # Standard cue point
                        cue_points.append({
                            'name': position_mark.get('Name', ''),
                            'position': float(position_mark.get('Start', 0)),
                            'type': 'cue'
                        })

                tracks[track_id] = {
                    'track_id': track_id,
                    'name': track.get('Name', ''),
                    'artist': track.get('Artist', ''),
                    'bpm': float(track.get('AverageBpm', 0)),
                    'duration_ms': int(float(track.get('TotalTime', 0)) * 1000),
                    'key': track.get('Tonality', ''),
                    'file_path': track.get('Location', ''),
                    'cue_points': cue_points
                }

    # Parse playlists from PLAYLISTS element
    playlists = []
    playlists_node = root.find('.//PLAYLISTS')

    if playlists_node is not None:
        # Skip the root node which contains all playlists
        for node in playlists_node.findall('.//NODE'):
            node_type = node.get('Type')
            node_name = node.get('Name')

            # Type 1 = Playlist (not folder)
            if node_type == '1' and node_name:
                track_ids = []
                for track in node.findall('TRACK'):
                    key = track.get('Key')
                    if key:
                        track_ids.append(key)

                playlists.append({
                    'name': node_name,
                    'track_ids': track_ids
                })

    return {
        'playlists': playlists,
        'tracks': tracks
    }


def get_playlist_tracks(xml_data: dict, playlist_name: str) -> list:
    """
    Get all tracks from a specific playlist.

    Args:
        xml_data: Parsed XML data from parse_rekordbox_xml()
        playlist_name: Name of the playlist to retrieve

    Returns:
        List of track dictionaries with keys: name, artist, bpm, duration_ms,
        cue_points, file_path, key
    """
    # Find the playlist by name
    playlist = None
    for pl in xml_data.get('playlists', []):
        if pl['name'] == playlist_name:
            playlist = pl
            break

    if not playlist:
        return []

    # Get tracks by their IDs
    tracks_dict = xml_data.get('tracks', {})
    tracks = []

    for track_id in playlist['track_ids']:
        if track_id in tracks_dict:
            tracks.append(tracks_dict[track_id])

    return tracks


def extract_track_audio_path(xml_data: dict, track_id: str) -> str:
    """
    Extract the actual audio file path from a track.

    Args:
        xml_data: Parsed XML data from parse_rekordbox_xml()
        track_id: The track ID to look up

    Returns:
        File path to the audio file, or empty string if not found
    """
    tracks = xml_data.get('tracks', {})

    if track_id not in tracks:
        return ''

    file_path = tracks[track_id].get('file_path', '')

    # Rekordbox uses file:// URLs, decode them
    if file_path.startswith('file://localhost/'):
        file_path = file_path.replace('file://localhost/', '')
    elif file_path.startswith('file:///'):
        file_path = file_path.replace('file:///', '')

    # URL decode the path
    from urllib.parse import unquote
    file_path = unquote(file_path)

    # On Windows, convert forward slashes to backslashes
    if os.name == 'nt':
        file_path = file_path.replace('/', '\\')

    return file_path


# ============================================================================
# XML MODIFICATION FUNCTIONS
# ============================================================================

# Rekordbox color mapping for memory cues (0-7 indices)
REKORDBOX_COLORS = {
    'pink': (255, 0, 204),      # 0
    'red': (255, 0, 0),         # 1
    'orange': (255, 153, 0),    # 2
    'yellow': (255, 255, 0),    # 3
    'green': (0, 255, 0),       # 4
    'aqua': (0, 255, 204),      # 5
    'blue': (0, 102, 255),      # 6
    'purple': (153, 51, 255),   # 7
}


def parse_rekordbox_xml_advanced(file_path: str):
    """
    Parse a Rekordbox XML file and return the full ElementTree for modification.

    Args:
        file_path: Path to the Rekordbox XML file

    Returns:
        lxml ElementTree object that can be modified

    Raises:
        FileNotFoundError: If XML file doesn't exist
        ValueError: If XML parsing fails
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"XML file not found: {file_path}")

    try:
        tree = etree.parse(file_path)
        return tree
    except Exception as e:
        raise ValueError(f"Failed to parse XML file: {str(e)}")


def _get_rgb_for_color(color: str) -> tuple:
    """
    Get RGB values for a color name.

    Args:
        color: Color name (e.g., 'red', 'orange', 'blue')

    Returns:
        Tuple of (red, green, blue) values (0-255)
    """
    color_lower = color.lower()
    if color_lower in REKORDBOX_COLORS:
        return REKORDBOX_COLORS[color_lower]

    # Default to white if color not found
    print(f"Warning: Unknown color '{color}', defaulting to white")
    return (255, 255, 255)


def insert_memory_cue(track_element, time_ms: float, name: str, color: str) -> None:
    """
    Insert a memory cue into a track's POSITION_MARK list.

    Rekordbox XML Format for Memory Cues:
    <POSITION_MARK Name="Cue Name" Type="0" Start="12.345"
                   Red="255" Green="0" Blue="0" />

    Args:
        track_element: lxml Element object for the TRACK
        time_ms: Cue position in milliseconds
        name: Cue point name
        color: Color name (e.g., 'red', 'orange', 'blue')

    Note:
        - Type="0" indicates a memory cue (non-hot cue)
        - Start is in seconds as a float
        - Red/Green/Blue are RGB color values (0-255)
    """
    # Convert milliseconds to seconds (Rekordbox uses seconds)
    time_seconds = time_ms / 1000.0

    # Get RGB color
    red, green, blue = _get_rgb_for_color(color)

    # Create POSITION_MARK element
    position_mark = etree.Element('POSITION_MARK')
    position_mark.set('Name', name)
    position_mark.set('Type', '0')  # 0 = memory cue
    position_mark.set('Start', f'{time_seconds:.3f}')
    position_mark.set('Red', str(red))
    position_mark.set('Green', str(green))
    position_mark.set('Blue', str(blue))

    # Add to track element
    track_element.append(position_mark)


def insert_hot_cue(track_element, time_ms: float, name: str, color: str, hot_cue_num: int = -1) -> None:
    """
    Insert a hot cue into a track's POSITION_MARK list.

    Rekordbox XML Format for Hot Cues:
    <POSITION_MARK Name="Drop" Type="0" Start="60.000" Num="0"
                   Red="255" Green="0" Blue="0" />

    Args:
        track_element: lxml Element object for the TRACK
        time_ms: Cue position in milliseconds
        name: Hot cue name
        color: Color name (e.g., 'red', 'orange', 'blue')
        hot_cue_num: Hot cue slot number (0-7), -1 for auto-assign to first available

    Note:
        - Type="0" with Num attribute indicates a hot cue
        - Num is the hot cue slot (0-7 for A-H)
        - Start is in seconds as a float
        - Red/Green/Blue are RGB color values (0-255)
    """
    # Convert milliseconds to seconds
    time_seconds = time_ms / 1000.0

    # Get RGB color
    red, green, blue = _get_rgb_for_color(color)

    # Auto-assign hot cue number if not specified
    if hot_cue_num == -1:
        # Find first available hot cue slot
        existing_hot_cues = set()
        for pm in track_element.findall('.//POSITION_MARK'):
            if pm.get('Num') is not None:
                try:
                    existing_hot_cues.add(int(pm.get('Num')))
                except ValueError:
                    pass

        # Find first available slot (0-7)
        for i in range(8):
            if i not in existing_hot_cues:
                hot_cue_num = i
                break

        if hot_cue_num == -1:
            print(f"Warning: All hot cue slots occupied, skipping hot cue '{name}'")
            return

    # Create POSITION_MARK element
    position_mark = etree.Element('POSITION_MARK')
    position_mark.set('Name', name)
    position_mark.set('Type', '0')  # Type 0 with Num = hot cue
    position_mark.set('Start', f'{time_seconds:.3f}')
    position_mark.set('Num', str(hot_cue_num))
    position_mark.set('Red', str(red))
    position_mark.set('Green', str(green))
    position_mark.set('Blue', str(blue))

    # Add to track element
    track_element.append(position_mark)


def remove_existing_cues(track_element, remove_memory: bool = True, remove_hot: bool = False) -> int:
    """
    Remove existing cue points from a track.

    Args:
        track_element: lxml Element object for the TRACK
        remove_memory: If True, remove memory cues (cues without Num attribute)
        remove_hot: If True, remove hot cues (cues with Num attribute)

    Returns:
        Number of cues removed

    Note:
        By default, only memory cues are removed to preserve existing hot cues.
        Set remove_hot=True to also clear hot cues.
    """
    removed_count = 0

    # Find all POSITION_MARK elements
    position_marks = track_element.findall('.//POSITION_MARK')

    for pm in position_marks:
        is_hot_cue = pm.get('Num') is not None

        should_remove = False
        if is_hot_cue and remove_hot:
            should_remove = True
        elif not is_hot_cue and remove_memory:
            should_remove = True

        if should_remove:
            track_element.remove(pm)
            removed_count += 1

    return removed_count


def export_modified_xml(tree, output_path: str = None) -> str:
    """
    Export the modified XML tree to a file with timestamp.

    Args:
        tree: lxml ElementTree object
        output_path: Optional custom output path. If None, creates in 'exports' directory

    Returns:
        Path to the exported XML file

    Raises:
        IOError: If file cannot be written

    Example output filename:
        exports/rekordbox_autocued_2025-01-15_14-32-05.xml
    """
    # Create exports directory if it doesn't exist
    if output_path is None:
        exports_dir = 'exports'
        if not os.path.exists(exports_dir):
            os.makedirs(exports_dir)

        # Generate timestamp filename
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_path = os.path.join(exports_dir, f'rekordbox_autocued_{timestamp}.xml')

    try:
        # Write XML with proper formatting
        tree.write(
            output_path,
            encoding='UTF-8',
            xml_declaration=True,
            pretty_print=True
        )

        return output_path

    except Exception as e:
        raise IOError(f"Failed to export XML: {str(e)}")


def get_track_element_by_id(tree, track_id: str):
    """
    Find a TRACK element by its TrackID attribute.

    Args:
        tree: lxml ElementTree object
        track_id: Track ID to search for

    Returns:
        lxml Element object for the TRACK, or None if not found
    """
    root = tree.getroot()
    collection = root.find('.//COLLECTION')

    if collection is None:
        return None

    for track in collection.findall('TRACK'):
        if track.get('TrackID') == track_id:
            return track

    return None
