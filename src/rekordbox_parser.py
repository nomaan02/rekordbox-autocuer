"""
Rekordbox XML parser for extracting playlist and track information.
"""
from lxml import etree
from typing import Dict, List, Optional
import os


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
