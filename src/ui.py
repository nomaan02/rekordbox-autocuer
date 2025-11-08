"""
PyQt5-based UI for Rekordbox Autocuer batch processing.
"""
import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QProgressBar, QFileDialog,
    QGraphicsView, QGraphicsScene, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPen, QColor, QPainter, QFont

from rekordbox_parser import parse_rekordbox_xml, get_playlist_tracks, extract_track_audio_path
from audio_processor import load_audio_file, generate_waveform_data
from batch_processor import process_track_batch


class WaveformCanvas(QGraphicsView):
    """Interactive waveform display canvas with click-to-mark functionality."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Waveform data
        self.waveform_data = []
        self.duration_seconds = 0
        self.bpm = 0
        self.drop_position = None  # Position in seconds where user marked the drop

        # Visual settings
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QColor(30, 30, 30))
        self.setMinimumHeight(200)

    def set_waveform(self, waveform_data, duration_seconds, bpm):
        """Set the waveform data and redraw."""
        self.waveform_data = waveform_data
        self.duration_seconds = duration_seconds
        self.bpm = bpm
        self.drop_position = None
        self.draw_waveform()

    def draw_waveform(self):
        """Draw the waveform, grid, and drop marker."""
        self.scene.clear()

        if not self.waveform_data or self.duration_seconds == 0:
            return

        width = self.viewport().width() - 20
        height = self.viewport().height() - 20

        # Draw BPM grid (bar lines)
        if self.bpm > 0:
            seconds_per_beat = 60.0 / self.bpm
            seconds_per_bar = seconds_per_beat * 4  # Assuming 4/4 time

            num_bars = int(self.duration_seconds / seconds_per_bar)

            grid_pen = QPen(QColor(60, 60, 60), 1)
            for i in range(num_bars + 1):
                bar_time = i * seconds_per_bar
                x = (bar_time / self.duration_seconds) * width + 10
                self.scene.addLine(x, 10, x, height + 10, grid_pen)

        # Draw waveform
        waveform_pen = QPen(QColor(100, 150, 255), 2)
        center_y = height / 2 + 10

        # Normalize waveform data
        if self.waveform_data:
            max_amplitude = max(self.waveform_data) if max(self.waveform_data) > 0 else 1

            for i in range(len(self.waveform_data) - 1):
                x1 = (i / len(self.waveform_data)) * width + 10
                x2 = ((i + 1) / len(self.waveform_data)) * width + 10

                # Normalize and scale amplitude
                amplitude1 = (self.waveform_data[i] / max_amplitude) * (height / 2)
                amplitude2 = (self.waveform_data[i + 1] / max_amplitude) * (height / 2)

                # Draw top half
                self.scene.addLine(x1, center_y - amplitude1, x2, center_y - amplitude2, waveform_pen)
                # Draw bottom half (mirrored)
                self.scene.addLine(x1, center_y + amplitude1, x2, center_y + amplitude2, waveform_pen)

        # Draw drop marker if set
        if self.drop_position is not None:
            marker_x = (self.drop_position / self.duration_seconds) * width + 10
            marker_pen = QPen(QColor(255, 50, 50), 3)
            self.scene.addLine(marker_x, 10, marker_x, height + 10, marker_pen)

            # Add timestamp label
            minutes = int(self.drop_position // 60)
            seconds = int(self.drop_position % 60)
            time_str = f"{minutes:02d}:{seconds:02d}"

            text = self.scene.addText(time_str)
            text.setDefaultTextColor(QColor(255, 50, 50))
            text.setPos(marker_x + 5, 10)

    def mousePressEvent(self, event):
        """Handle mouse click to mark drop position."""
        if event.button() == Qt.LeftButton and self.waveform_data:
            # Convert click position to time
            scene_pos = self.mapToScene(event.pos())
            width = self.viewport().width() - 20

            relative_x = scene_pos.x() - 10
            if 0 <= relative_x <= width:
                self.drop_position = (relative_x / width) * self.duration_seconds
                self.draw_waveform()

    def resizeEvent(self, event):
        """Redraw on resize."""
        super().resizeEvent(event)
        self.draw_waveform()

    def get_drop_position(self):
        """Get the marked drop position in seconds."""
        return self.drop_position


class RecordboxAutocuerApp(QMainWindow):
    """Main application window for Rekordbox Autocuer."""

    def __init__(self):
        super().__init__()

        # Data
        self.xml_data = None
        self.xml_file_path = None  # Store original XML path for export
        self.current_playlist_name = None  # Store current playlist name
        self.current_playlist_tracks = []
        self.current_track_index = 0
        self.drop_markers = {}  # track_id -> drop_position mapping

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Rekordbox Autocuer - Batch Drop Marker")
        self.setGeometry(100, 100, 1200, 800)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # === TOP SECTION: File selection and playlist ===
        file_layout = QHBoxLayout()

        self.xml_path_label = QLabel("No XML file loaded")
        self.xml_path_label.setStyleSheet("color: gray;")
        file_layout.addWidget(self.xml_path_label)

        self.browse_button = QPushButton("Browse XML...")
        self.browse_button.clicked.connect(self.browse_xml)
        file_layout.addWidget(self.browse_button)

        self.playlist_combo = QComboBox()
        self.playlist_combo.setEnabled(False)
        self.playlist_combo.currentTextChanged.connect(self.on_playlist_selected)
        file_layout.addWidget(self.playlist_combo)

        self.start_button = QPushButton("Start Processing")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_processing)
        self.start_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        file_layout.addWidget(self.start_button)

        main_layout.addLayout(file_layout)

        # === PROGRESS BAR ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat("Track %v of %m")
        self.progress_bar.setMinimum(0)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # === TRACK METADATA SECTION ===
        metadata_frame = QFrame()
        metadata_frame.setFrameStyle(QFrame.Box)
        metadata_layout = QHBoxLayout()

        self.title_label = QLabel("Title: --")
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))
        metadata_layout.addWidget(self.title_label)

        self.artist_label = QLabel("Artist: --")
        metadata_layout.addWidget(self.artist_label)

        self.bpm_label = QLabel("BPM: --")
        metadata_layout.addWidget(self.bpm_label)

        self.key_label = QLabel("Key: --")
        metadata_layout.addWidget(self.key_label)

        self.duration_label = QLabel("Duration: --")
        metadata_layout.addWidget(self.duration_label)

        metadata_frame.setLayout(metadata_layout)
        main_layout.addWidget(metadata_frame)

        # === WAVEFORM CANVAS ===
        self.waveform_canvas = WaveformCanvas()
        main_layout.addWidget(self.waveform_canvas, stretch=1)

        # === CONTROL BUTTONS ===
        button_layout = QHBoxLayout()

        self.mark_drop_button = QPushButton("Mark Drop (Click waveform or press this)")
        self.mark_drop_button.setEnabled(False)
        self.mark_drop_button.clicked.connect(self.mark_drop_auto)
        self.mark_drop_button.setStyleSheet("background-color: #2196F3; color: white; font-size: 14px; padding: 10px;")
        button_layout.addWidget(self.mark_drop_button)

        self.skip_button = QPushButton("Skip Track")
        self.skip_button.setEnabled(False)
        self.skip_button.clicked.connect(self.skip_track)
        self.skip_button.setStyleSheet("background-color: #FF9800; color: white; font-size: 14px; padding: 10px;")
        button_layout.addWidget(self.skip_button)

        main_layout.addLayout(button_layout)

        # === EXPORT BUTTON (shown after marking complete) ===
        export_layout = QHBoxLayout()

        self.export_button = QPushButton("Process & Export XML")
        self.export_button.setEnabled(False)
        self.export_button.setVisible(False)
        self.export_button.clicked.connect(self.export_xml)
        self.export_button.setStyleSheet("background-color: #4CAF50; color: white; font-size: 16px; font-weight: bold; padding: 15px;")
        export_layout.addWidget(self.export_button)

        main_layout.addLayout(export_layout)

        # Status bar
        self.statusBar().showMessage("Ready. Load a Rekordbox XML file to begin.")

    def browse_xml(self):
        """Open file dialog to select Rekordbox XML export."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Rekordbox XML Export",
            "",
            "XML Files (*.xml);;All Files (*)"
        )

        if file_path:
            try:
                self.xml_data = parse_rekordbox_xml(file_path)
                self.xml_file_path = file_path  # Store for later export
                self.xml_path_label.setText(f"Loaded: {os.path.basename(file_path)}")
                self.xml_path_label.setStyleSheet("color: green;")

                # Populate playlist dropdown
                self.playlist_combo.clear()
                playlists = self.xml_data.get('playlists', [])

                if playlists:
                    self.playlist_combo.addItem("-- Select Playlist --")
                    for playlist in playlists:
                        self.playlist_combo.addItem(playlist['name'])
                    self.playlist_combo.setEnabled(True)
                else:
                    QMessageBox.warning(self, "No Playlists", "No playlists found in XML file.")

                self.statusBar().showMessage(f"Loaded {len(playlists)} playlists")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load XML: {str(e)}")
                self.xml_path_label.setText("Error loading XML")
                self.xml_path_label.setStyleSheet("color: red;")

    def on_playlist_selected(self, playlist_name):
        """Handle playlist selection."""
        if playlist_name and playlist_name != "-- Select Playlist --":
            tracks = get_playlist_tracks(self.xml_data, playlist_name)

            if tracks:
                self.current_playlist_name = playlist_name  # Store playlist name
                self.current_playlist_tracks = tracks
                self.start_button.setEnabled(True)
                self.statusBar().showMessage(f"Selected playlist: {playlist_name} ({len(tracks)} tracks)")
            else:
                QMessageBox.warning(self, "Empty Playlist", f"Playlist '{playlist_name}' has no tracks.")

    def start_processing(self):
        """Start the batch processing workflow."""
        if not self.current_playlist_tracks:
            return

        self.current_track_index = 0
        self.drop_markers = {}

        # Update progress bar
        self.progress_bar.setMaximum(len(self.current_playlist_tracks))
        self.progress_bar.setValue(0)

        # Disable start button and playlist selection
        self.start_button.setEnabled(False)
        self.playlist_combo.setEnabled(False)
        self.browse_button.setEnabled(False)

        # Enable control buttons
        self.mark_drop_button.setEnabled(True)
        self.skip_button.setEnabled(True)

        # Load first track
        self.load_current_track()

    def load_current_track(self):
        """Load and display the current track."""
        if self.current_track_index >= len(self.current_playlist_tracks):
            # All tracks processed
            self.finish_processing()
            return

        track = self.current_playlist_tracks[self.current_track_index]

        # Update progress
        self.progress_bar.setValue(self.current_track_index + 1)

        # Update metadata display
        self.title_label.setText(f"Title: {track['name']}")
        self.artist_label.setText(f"Artist: {track['artist']}")
        self.bpm_label.setText(f"BPM: {track['bpm']:.1f}")
        self.key_label.setText(f"Key: {track['key']}")

        duration_seconds = track['duration_ms'] / 1000
        minutes = int(duration_seconds // 60)
        seconds = int(duration_seconds % 60)
        self.duration_label.setText(f"Duration: {minutes}:{seconds:02d}")

        # Load audio and generate waveform
        file_path = extract_track_audio_path(self.xml_data, track['track_id'])

        if file_path and os.path.exists(file_path):
            try:
                self.statusBar().showMessage(f"Loading audio: {track['name']}...")
                QApplication.processEvents()  # Update UI

                audio_data, sample_rate = load_audio_file(file_path)
                waveform_data = generate_waveform_data(audio_data, sample_rate, bins=1024)

                self.waveform_canvas.set_waveform(waveform_data, duration_seconds, track['bpm'])

                self.statusBar().showMessage(f"Track {self.current_track_index + 1}/{len(self.current_playlist_tracks)}: {track['name']}")

            except Exception as e:
                QMessageBox.warning(self, "Audio Load Error", f"Failed to load audio: {str(e)}\n\nSkipping track.")
                self.skip_track()
        else:
            QMessageBox.warning(self, "File Not Found", f"Audio file not found:\n{file_path}\n\nSkipping track.")
            self.skip_track()

    def mark_drop_auto(self):
        """Automatically mark drop at the current position or prompt user."""
        drop_pos = self.waveform_canvas.get_drop_position()

        if drop_pos is None:
            QMessageBox.information(
                self,
                "Mark Drop",
                "Click on the waveform to mark the drop position, then press this button or move to the next track."
            )
            return

        # Save drop marker
        track = self.current_playlist_tracks[self.current_track_index]
        self.drop_markers[track['track_id']] = drop_pos

        # Move to next track
        self.next_track()

    def skip_track(self):
        """Skip the current track without marking."""
        self.next_track()

    def next_track(self):
        """Move to the next track."""
        self.current_track_index += 1
        self.load_current_track()

    def finish_processing(self):
        """Finish the batch processing workflow."""
        # Check if any tracks were marked
        if len(self.drop_markers) == 0:
            QMessageBox.information(
                self,
                "No Tracks Marked",
                "No drops were marked. Please mark at least one track to export."
            )
        else:
            QMessageBox.information(
                self,
                "Marking Complete",
                f"Batch marking complete!\n\nMarked drops for {len(self.drop_markers)} tracks.\n\nClick 'Process & Export XML' to generate the modified Rekordbox file."
            )

            # Show and enable export button
            self.export_button.setVisible(True)
            self.export_button.setEnabled(True)

        # Re-enable controls
        self.start_button.setEnabled(True)
        self.playlist_combo.setEnabled(True)
        self.browse_button.setEnabled(True)
        self.mark_drop_button.setEnabled(False)
        self.skip_button.setEnabled(False)

        # Clear display
        self.waveform_canvas.set_waveform([], 0, 0)
        self.title_label.setText("Title: --")
        self.artist_label.setText("Artist: --")
        self.bpm_label.setText("BPM: --")
        self.key_label.setText("Key: --")
        self.duration_label.setText("Duration: --")

        if len(self.drop_markers) > 0:
            self.statusBar().showMessage("Marking complete. Click 'Process & Export XML' to continue.")
        else:
            self.statusBar().showMessage("Processing complete. Ready for next batch.")

    def export_xml(self):
        """Process marked tracks and export modified XML."""
        if not self.drop_markers:
            QMessageBox.warning(
                self,
                "No Tracks Marked",
                "No tracks have been marked with drop points. Please mark tracks first."
            )
            return

        if not self.xml_file_path:
            QMessageBox.critical(
                self,
                "Error",
                "Original XML file path not found. Please reload the XML file."
            )
            return

        # Confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirm Export",
            f"Process {len(self.drop_markers)} tracks and generate modified XML?\n\n"
            f"This will calculate and insert cue points based on the marked drops.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply == QMessageBox.No:
            return

        # Disable export button during processing
        self.export_button.setEnabled(False)
        self.statusBar().showMessage("Processing tracks and generating XML...")
        QApplication.processEvents()

        try:
            # Call batch processor
            output_path = process_track_batch(
                self.xml_file_path,
                self.drop_markers
            )

            # Success dialog with instructions
            success_msg = QMessageBox(self)
            success_msg.setIcon(QMessageBox.Information)
            success_msg.setWindowTitle("Export Successful")
            success_msg.setText(f"Modified XML exported successfully!")
            success_msg.setInformativeText(
                f"File saved to:\n{output_path}\n\n"
                f"To import into Rekordbox:\n"
                f"1. Open Rekordbox\n"
                f"2. Go to File > Import Collection\n"
                f"3. Select the exported XML file\n"
                f"4. Rekordbox will merge the cue points with your existing library\n\n"
                f"Note: This preserves your existing tracks and only updates cue points."
            )
            success_msg.setStandardButtons(QMessageBox.Ok)
            success_msg.exec_()

            self.statusBar().showMessage(f"Export complete: {output_path}")

            # Reset for next batch
            self.export_button.setEnabled(True)

        except FileNotFoundError as e:
            QMessageBox.critical(
                self,
                "File Not Found",
                f"XML file not found:\n{str(e)}"
            )
            self.export_button.setEnabled(True)

        except ValueError as e:
            QMessageBox.critical(
                self,
                "Processing Error",
                f"Failed to process tracks:\n{str(e)}"
            )
            self.export_button.setEnabled(True)

        except IOError as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export XML:\n{str(e)}"
            )
            self.export_button.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Unexpected Error",
                f"An unexpected error occurred:\n{str(e)}"
            )
            self.export_button.setEnabled(True)


def main():
    """Run the application."""
    app = QApplication(sys.argv)
    window = RecordboxAutocuerApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
