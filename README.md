# Rekordbox AutoCuer

Batch cue-point automation for Rekordbox DJ software with manual drop marking.

## Setup

Python 3.9+ required.

See requirements.txt for dependencies.

## Usage

\\\ash
python src/main.py
\\\

## Workflow

1. Export your Rekordbox collection as XML (File > Export Collection in xml format)
2. Load the XML in AutoCuer
3. Select a playlist
4. Mark the drop point on each track (or skip)
5. Click "Process & Export"
6. Import the generated XML back into Rekordbox (Preferences > Bridge > Imported Library)
7. Export to USB for CDJ playback
