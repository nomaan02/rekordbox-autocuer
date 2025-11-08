"""
Unit tests for cue_generator module.

Run with: python -m pytest src/test_cue_generator.py -v
"""
import pytest
from cue_generator import (
    calculate_cue_positions,
    snap_to_grid,
    validate_cue_positions,
    format_cue_time
)


class TestCalculateCuePositions:
    """Tests for calculate_cue_positions function."""

    def test_120_bpm_drop_at_60_seconds(self):
        """Test standard case: 120 BPM track with drop at 60 seconds."""
        bpm = 120.0
        drop_time_ms = 60000.0  # 60 seconds
        track_duration_ms = 180000.0  # 3 minutes

        cues = calculate_cue_positions(bpm, drop_time_ms, track_duration_ms)

        # At 120 BPM:
        # - Beat duration = 60000 / 120 = 500ms
        # - Bar duration = 500 * 4 = 2000ms
        # - 16 bars = 32000ms = 32 seconds
        # - 32 bars = 64000ms = 64 seconds

        # Expected cues:
        # -32 bars: 60000 - 64000 = -4000 (out of bounds, skip)
        # -16 bars: 60000 - 32000 = 28000 (28 seconds)
        # Drop: 60000 (60 seconds)
        # +16 bars: 60000 + 32000 = 92000 (92 seconds)
        # +32 bars: 60000 + 64000 = 124000 (124 seconds)

        assert len(cues) == 4  # Only 4 cues fit within bounds

        # Check first cue (-16 bars)
        assert cues[0][0] == 28000.0
        assert cues[0][1] == "memory"
        assert cues[0][2] == "-16 bars"
        assert cues[0][3] == "yellow"

        # Check drop
        assert cues[1][0] == 60000.0
        assert cues[1][1] == "hot"
        assert cues[1][2] == "Drop"
        assert cues[1][3] == "red"

        # Check +16 bars
        assert cues[2][0] == 92000.0
        assert cues[2][1] == "memory"
        assert cues[2][2] == "+16 bars"
        assert cues[2][3] == "blue"

        # Check +32 bars
        assert cues[3][0] == 124000.0
        assert cues[3][1] == "memory"
        assert cues[3][2] == "+32 bars"
        assert cues[3][3] == "aqua"

    def test_140_bpm_drop_at_90_seconds(self):
        """Test faster tempo: 140 BPM track with drop at 90 seconds."""
        bpm = 140.0
        drop_time_ms = 90000.0  # 90 seconds
        track_duration_ms = 240000.0  # 4 minutes

        cues = calculate_cue_positions(bpm, drop_time_ms, track_duration_ms)

        # At 140 BPM:
        # - Beat duration = 60000 / 140 = 428.57ms
        # - Bar duration = 428.57 * 4 = 1714.29ms
        # - 16 bars = 27428.57ms = ~27.4 seconds
        # - 32 bars = 54857.14ms = ~54.9 seconds

        # Expected cues (all should fit):
        # -32 bars: 90000 - 54857.14 = 35142.86
        # -16 bars: 90000 - 27428.57 = 62571.43
        # Drop: 90000
        # +16 bars: 90000 + 27428.57 = 117428.57
        # +32 bars: 90000 + 54857.14 = 144857.14

        assert len(cues) == 5

        # Verify timing calculations
        bar_duration = (60000.0 / 140.0) * 4

        assert abs(cues[0][0] - (90000.0 - 32 * bar_duration)) < 0.01
        assert abs(cues[1][0] - (90000.0 - 16 * bar_duration)) < 0.01
        assert cues[2][0] == 90000.0
        assert abs(cues[3][0] - (90000.0 + 16 * bar_duration)) < 0.01
        assert abs(cues[4][0] - (90000.0 + 32 * bar_duration)) < 0.01

    def test_very_short_track(self):
        """Test edge case: Track too short for all cues."""
        bpm = 128.0
        drop_time_ms = 30000.0  # 30 seconds
        track_duration_ms = 60000.0  # 1 minute - very short

        cues = calculate_cue_positions(bpm, drop_time_ms, track_duration_ms)

        # At 128 BPM:
        # - Bar duration = (60000 / 128) * 4 = 1875ms
        # - 16 bars = 30000ms
        # - 32 bars = 60000ms

        # Expected:
        # -32 bars: 30000 - 60000 = -30000 (out of bounds)
        # -16 bars: 30000 - 30000 = 0 (at start, valid)
        # Drop: 30000 (valid)
        # +16 bars: 30000 + 30000 = 60000 (at end, valid)
        # +32 bars: 30000 + 60000 = 90000 (out of bounds)

        assert len(cues) == 3

        assert cues[0][0] == 0.0  # -16 bars at start
        assert cues[1][0] == 30000.0  # Drop
        assert cues[2][0] == 60000.0  # +16 bars at end

    def test_drop_near_start(self):
        """Test edge case: Drop very close to track start."""
        bpm = 120.0
        drop_time_ms = 10000.0  # 10 seconds
        track_duration_ms = 180000.0  # 3 minutes

        cues = calculate_cue_positions(bpm, drop_time_ms, track_duration_ms)

        # -32 bars and -16 bars will be before track start
        # Only Drop and after cues should appear

        assert len(cues) == 3  # Drop, +16, +32

        assert cues[0][0] == 10000.0  # Drop
        assert cues[0][2] == "Drop"

    def test_drop_near_end(self):
        """Test edge case: Drop very close to track end."""
        bpm = 120.0
        drop_time_ms = 170000.0  # 170 seconds (2:50)
        track_duration_ms = 180000.0  # 3 minutes

        cues = calculate_cue_positions(bpm, drop_time_ms, track_duration_ms)

        # +16 bars and +32 bars will be after track end
        # Only before cues and Drop should appear

        assert len(cues) == 3  # -32, -16, Drop

        assert cues[-1][0] == 170000.0  # Drop is last cue
        assert cues[-1][2] == "Drop"

    def test_very_fast_bpm(self):
        """Test edge case: Very fast BPM (180)."""
        bpm = 180.0
        drop_time_ms = 60000.0
        track_duration_ms = 180000.0

        cues = calculate_cue_positions(bpm, drop_time_ms, track_duration_ms)

        # At 180 BPM, bars are shorter, so more cues should fit
        # Bar duration = (60000 / 180) * 4 = 1333.33ms
        # 16 bars = 21333.33ms
        # 32 bars = 42666.67ms

        # All cues should fit
        assert len(cues) == 5

        bar_duration = (60000.0 / 180.0) * 4
        assert abs(cues[0][0] - (60000.0 - 32 * bar_duration)) < 0.01

    def test_invalid_bpm(self):
        """Test error handling: Invalid BPM."""
        with pytest.raises(ValueError, match="BPM must be positive"):
            calculate_cue_positions(0, 60000.0, 180000.0)

        with pytest.raises(ValueError, match="BPM must be positive"):
            calculate_cue_positions(-120.0, 60000.0, 180000.0)

    def test_invalid_drop_time(self):
        """Test error handling: Invalid drop time."""
        with pytest.raises(ValueError, match="Drop time cannot be negative"):
            calculate_cue_positions(120.0, -1000.0, 180000.0)

    def test_invalid_track_duration(self):
        """Test error handling: Invalid track duration."""
        with pytest.raises(ValueError, match="Track duration must be positive"):
            calculate_cue_positions(120.0, 60000.0, 0)

        with pytest.raises(ValueError, match="Track duration must be positive"):
            calculate_cue_positions(120.0, 60000.0, -180000.0)

    def test_three_four_time_signature(self):
        """Test non-standard time signature: 3/4."""
        bpm = 120.0
        drop_time_ms = 60000.0
        track_duration_ms = 180000.0

        cues = calculate_cue_positions(bpm, drop_time_ms, track_duration_ms, "3/4")

        # At 120 BPM with 3/4 time:
        # - Bar duration = (60000 / 120) * 3 = 1500ms (shorter bars)

        # 16 bars = 24000ms
        # -16 bars: 60000 - 24000 = 36000

        assert any(abs(cue[0] - 36000.0) < 0.01 for cue in cues)


class TestSnapToGrid:
    """Tests for snap_to_grid function."""

    def test_snap_to_quarter_notes(self):
        """Test snapping to quarter note grid at 120 BPM."""
        bpm = 120.0

        # At 120 BPM, beat = 500ms
        assert snap_to_grid(1230.0, bpm, 4) == 1000.0  # Snap to 2nd beat
        assert snap_to_grid(1750.0, bpm, 4) == 2000.0  # Snap to 4th beat
        assert snap_to_grid(260.0, bpm, 4) == 500.0    # Snap to 1st beat
        assert snap_to_grid(240.0, bpm, 4) == 0.0      # Snap to start

    def test_snap_to_eighth_notes(self):
        """Test snapping to eighth note grid at 120 BPM."""
        bpm = 120.0

        # At 120 BPM, eighth note = 250ms
        assert snap_to_grid(1230.0, bpm, 8) == 1250.0
        assert snap_to_grid(1100.0, bpm, 8) == 1000.0

    def test_snap_already_on_grid(self):
        """Test snapping value already on grid."""
        bpm = 120.0
        assert snap_to_grid(1000.0, bpm, 4) == 1000.0
        assert snap_to_grid(2000.0, bpm, 4) == 2000.0

    def test_snap_invalid_bpm(self):
        """Test error handling: Invalid BPM."""
        with pytest.raises(ValueError, match="BPM must be positive"):
            snap_to_grid(1000.0, 0, 4)

    def test_snap_invalid_grid_resolution(self):
        """Test error handling: Invalid grid resolution."""
        with pytest.raises(ValueError, match="Grid resolution must be positive"):
            snap_to_grid(1000.0, 120.0, 0)


class TestValidateCuePositions:
    """Tests for validate_cue_positions function."""

    def test_valid_cues(self):
        """Test validation of valid cue positions."""
        cues = [
            (10000.0, "memory", "Cue1", "orange"),
            (30000.0, "hot", "Drop", "red"),
            (50000.0, "memory", "Cue2", "blue"),
        ]

        is_valid, warnings = validate_cue_positions(cues, 180000.0, 120.0)

        assert is_valid
        assert len(warnings) == 0

    def test_cue_before_start(self):
        """Test validation catches cue before track start."""
        cues = [
            (-1000.0, "memory", "BadCue", "red"),
            (30000.0, "hot", "Drop", "red"),
        ]

        is_valid, warnings = validate_cue_positions(cues, 180000.0, 120.0)

        assert not is_valid
        assert any("before track start" in w for w in warnings)

    def test_cue_after_end(self):
        """Test validation catches cue after track end."""
        cues = [
            (30000.0, "hot", "Drop", "red"),
            (200000.0, "memory", "BadCue", "blue"),
        ]

        is_valid, warnings = validate_cue_positions(cues, 180000.0, 120.0)

        assert not is_valid
        assert any("after track end" in w for w in warnings)

    def test_cues_too_close(self):
        """Test validation catches cues that are too close together."""
        cues = [
            (30000.0, "memory", "Cue1", "red"),
            (30500.0, "hot", "Cue2", "blue"),  # Only 500ms apart
        ]

        is_valid, warnings = validate_cue_positions(cues, 180000.0, 120.0)

        # Should still be valid but with warning
        assert any("too close together" in w for w in warnings)

    def test_short_track_warning(self):
        """Test validation warns about short tracks."""
        cues = [
            (5000.0, "hot", "Drop", "red"),
        ]

        is_valid, warnings = validate_cue_positions(cues, 30000.0, 120.0)

        assert is_valid
        assert any("too short" in w for w in warnings)

    def test_unusual_bpm_warning(self):
        """Test validation warns about unusual BPM."""
        cues = [
            (30000.0, "hot", "Drop", "red"),
        ]

        # Very slow BPM
        is_valid, warnings = validate_cue_positions(cues, 180000.0, 40.0)
        assert any("outside typical range" in w for w in warnings)

        # Very fast BPM
        is_valid, warnings = validate_cue_positions(cues, 180000.0, 220.0)
        assert any("outside typical range" in w for w in warnings)

    def test_empty_cues(self):
        """Test validation of empty cue list."""
        is_valid, warnings = validate_cue_positions([], 180000.0, 120.0)

        assert is_valid
        assert any("No cues generated" in w for w in warnings)


class TestFormatCueTime:
    """Tests for format_cue_time function."""

    def test_format_basic_times(self):
        """Test formatting basic time values."""
        assert format_cue_time(0.0) == "00:00"
        assert format_cue_time(5000.0) == "00:05"
        assert format_cue_time(30000.0) == "00:30"
        assert format_cue_time(60000.0) == "01:00"

    def test_format_longer_times(self):
        """Test formatting longer time values."""
        assert format_cue_time(65000.0) == "01:05"
        assert format_cue_time(125000.0) == "02:05"
        assert format_cue_time(600000.0) == "10:00"

    def test_format_rounds_down(self):
        """Test that formatting rounds down milliseconds."""
        assert format_cue_time(5999.0) == "00:05"  # 5.999s rounds to 5s
        assert format_cue_time(59999.0) == "00:59"  # 59.999s rounds to 59s


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_workflow(self):
        """Test complete workflow: calculate, validate, format."""
        # Generate cues
        bpm = 128.0
        drop_time_ms = 90000.0
        track_duration_ms = 240000.0

        cues = calculate_cue_positions(bpm, drop_time_ms, track_duration_ms)

        # Validate
        is_valid, warnings = validate_cue_positions(cues, track_duration_ms, bpm)

        assert is_valid
        assert len(cues) == 5  # All 5 cues should fit

        # Format times
        formatted_times = [format_cue_time(cue[0]) for cue in cues]

        # Verify all times are properly formatted
        for time_str in formatted_times:
            assert ":" in time_str
            parts = time_str.split(":")
            assert len(parts) == 2
            assert parts[0].isdigit()
            assert parts[1].isdigit()

    def test_snap_drop_time_before_calculation(self):
        """Test snapping drop time to grid before calculating cues."""
        bpm = 120.0
        user_marked_drop = 60123.0  # User clicked slightly off-beat

        # Snap to grid first
        snapped_drop = snap_to_grid(user_marked_drop, bpm, 4)
        assert snapped_drop == 60000.0  # Snapped to exact beat

        # Then calculate cues with snapped time
        cues = calculate_cue_positions(bpm, snapped_drop, 180000.0)

        # All cue times should be exact multiples of bar duration
        bar_duration = (60000.0 / bpm) * 4
        for cue_time, _, _, _ in cues:
            # Check if time is close to a bar boundary
            remainder = cue_time % bar_duration
            assert remainder == 0.0 or abs(remainder - bar_duration) < 0.01
