# Rekordbox AutoCuer

Batch cue-point automation for Rekordbox DJ software with manual drop marking.

## Features

- **XML Parser**: Load and parse Rekordbox XML exports
- **Playlist Browser**: Select and process entire playlists
- **Interactive Waveform Display**: Visual waveform with BPM grid overlay
- **Click-to-Mark**: Click anywhere on the waveform to mark drop points
- **Batch Processing**: Process multiple tracks in sequence
- **Progress Tracking**: Visual progress bar showing track position

## Setup

**Requirements:** Python 3.9+

**Install dependencies:**
```bash
pip install -r requirements.txt
```

## Usage

**Run the application:**
```bash
python main.py
```

## Workflow

1. **Export from Rekordbox**: File → Export Collection in XML format
2. **Load XML**: Click "Browse XML..." in the app
3. **Select Playlist**: Choose a playlist from the dropdown
4. **Start Processing**: Click "Start Processing" button
5. **Mark Drops**: For each track:
   - Click on the waveform where the drop occurs (red line will appear)
   - Press "Mark Drop" button or skip to next track
   - Or press "Skip Track" to skip without marking
6. **Complete**: When done, drop markers are saved (ready for export in Phase 3)

## Project Structure

```
rekordbox-autocuer/
├── src/
│   ├── rekordbox_parser.py   # XML parsing functions
│   ├── audio_processor.py     # Audio loading and waveform generation
│   └── ui.py                  # PyQt5 GUI application
├── main.py                    # Application entry point
└── requirements.txt           # Python dependencies
```

## Current Phase: Phase 2 - UI Framework ✓

### Completed
- ✅ XML parser with playlist and track extraction
- ✅ Audio loading with librosa
- ✅ Waveform visualization with RMS amplitude
- ✅ Interactive GUI with PyQt5
- ✅ Click-to-mark drop point functionality
- ✅ BPM-based grid overlay
- ✅ Batch processing workflow

### Next Phase: Phase 3 - XML Export
- Save marked drop points back to Rekordbox XML format
- Generate cue points at marked positions
- Export modified XML for re-import to Rekordbox
