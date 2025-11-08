# Rekordbox AutoCuer

Batch cue-point automation for Rekordbox DJ software with manual drop marking.

## Features

- **XML Parser**: Load and parse Rekordbox XML exports
- **Playlist Browser**: Select and process entire playlists
- **Interactive Waveform Display**: Visual waveform with BPM grid overlay
- **Click-to-Mark**: Click anywhere on the waveform to mark drop points
- **Batch Processing**: Process multiple tracks in sequence
- **Progress Tracking**: Visual progress bar showing track position
- **BPM-Based Cue Generation**: Automatically calculates cue points at ±16/±32 bars from drop
- **XML Export**: Generates modified Rekordbox XML with inserted cue points

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
   - Press "Mark Drop" button to save and move to next track
   - Or press "Skip Track" to skip without marking
6. **Process & Export**: After marking all tracks:
   - Click "Process & Export XML" button
   - The app will calculate cue points and generate modified XML
   - File saved to `exports/rekordbox_autocued_YYYY-MM-DD_HH-MM-SS.xml`
7. **Import to Rekordbox**:
   - Open Rekordbox
   - Go to File → Import Collection
   - Select the exported XML file
   - Rekordbox will merge the cue points with your existing library

## Project Structure

```
rekordbox-autocuer/
├── src/
│   ├── rekordbox_parser.py    # XML parsing and modification
│   ├── audio_processor.py      # Audio loading and waveform generation
│   ├── cue_generator.py        # BPM-based cue calculation engine
│   ├── batch_processor.py      # Batch processing workflow
│   ├── ui.py                   # PyQt5 GUI application
│   └── test_cue_generator.py   # Unit tests for cue generation
├── exports/                    # Generated XML files (created automatically)
├── main.py                     # Application entry point
└── requirements.txt            # Python dependencies
```

## Cue Point Layout

For each marked drop, the app generates 5 cue points:

| Position | Type | Name | Color |
|----------|------|------|-------|
| Drop - 32 bars | Memory | "-32 bars" | Orange |
| Drop - 16 bars | Memory | "-16 bars" | Yellow |
| Drop | Hot Cue | "Drop" | Red |
| Drop + 16 bars | Memory | "+16 bars" | Blue |
| Drop + 32 bars | Memory | "+32 bars" | Aqua |

Bar calculations are based on track BPM and 4/4 time signature.

## Development Status

### ✅ Phase 1: XML Parser & Audio Loader
- XML parsing with lxml
- Playlist and track extraction
- Audio loading with librosa
- Waveform generation

### ✅ Phase 2: UI Framework
- PyQt5 GUI with interactive waveform
- Click-to-mark drop functionality
- BPM-based grid overlay
- Batch processing workflow

### ✅ Phase 3: Cue Generation Engine
- BPM-based bar calculations
- Cue position validation
- Grid snapping functionality
- Comprehensive unit tests (27 tests)

### ✅ Phase 4: XML Export
- XML modification functions
- Memory cue and hot cue insertion
- Batch processing with logging
- Timestamped exports
- Error handling and validation

## Testing

Run unit tests:
```bash
python -m pytest src/test_cue_generator.py -v
```

All 27 tests should pass, covering:
- Standard BPM cases (120, 128, 140, 180)
- Edge cases (short tracks, drop near start/end)
- Grid snapping
- Validation
- Error handling
