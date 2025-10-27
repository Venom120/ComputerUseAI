import numpy as np
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.capture.screen_capture import ScreenCapture, ScreenCaptureConfig
from src.capture.audio_capture import AudioCapture, AudioCaptureConfig
from src.capture.event_tracker import EventTracker, EventTrackerConfig


class TestScreenCapture:
    def test_initialization(self):
        config = ScreenCaptureConfig(fps=3, quality=70)
        with tempfile.TemporaryDirectory() as temp_dir:
            capture = ScreenCapture(temp_dir, config)
            assert capture.config.fps == 3
            assert capture.config.quality == 70
            assert capture.output_dir == Path(temp_dir)

    def test_frame_difference_ratio(self):
        config = ScreenCaptureConfig()
        with tempfile.TemporaryDirectory() as temp_dir:
            capture = ScreenCapture(temp_dir, config)
            
            # Test with identical frames
            import numpy as np
            frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
            frame2 = np.zeros((100, 100, 3), dtype=np.uint8)
            ratio = capture._frame_difference_ratio(frame1, frame2)
            assert ratio == 0.0
            
            # Test with completely different frames
            frame3 = np.ones((100, 100, 3), dtype=np.uint8) * 255
            ratio = capture._frame_difference_ratio(frame1, frame3)
            assert ratio == 1.0

    @patch('src.capture.screen_capture.mss.mss')
    def test_grab_frame(self, mock_mss):
        config = ScreenCaptureConfig()
        with tempfile.TemporaryDirectory() as temp_dir:
            capture = ScreenCapture(temp_dir, config)
            
            # Mock mss grab to return a valid screenshot object
            mock_sct = Mock()
            # Simulate a 100x100 BGRX image (common mss format)
            mock_sct_img_data = np.zeros((100, 100, 4), dtype=np.uint8)
            mock_sct_img_data[:, :, 0] = 255 # Blue channel
            mock_sct_img_data[:, :, 3] = 255 # Alpha channel
            
            mock_sct.grab.return_value = mock_sct_img_data
            mock_sct.monitors = [{"top": 0, "left": 0, "width": 1920, "height": 1080}]
            capture._mss = mock_sct
            
            frame = capture._grab()
            assert frame is not None
            assert frame.shape == (100, 100, 3) # Expecting BGR frame after processing
            assert np.array_equal(frame[:, :, 0], np.ones((100, 100)) * 255) # Check blue channel

class TestAudioCapture:
    def test_initialization(self):
        config = AudioCaptureConfig(sample_rate=16000, channels=1)
        with tempfile.TemporaryDirectory() as temp_dir:
            capture = AudioCapture(temp_dir, config)
            assert capture.config.sample_rate == 16000
            assert capture.config.channels == 1
            assert capture.output_dir == Path(temp_dir)

    def test_contains_voice_no_vad(self):
        config = AudioCaptureConfig(use_vad=False)
        with tempfile.TemporaryDirectory() as temp_dir:
            capture = AudioCapture(temp_dir, config)
            import numpy as np
            chunk = np.random.rand(1000, 1)
            result = capture._contains_voice(chunk)
            assert result is True  # Should always return True when VAD is disabled


class TestEventTracker:
    def test_initialization(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = EventTrackerConfig(log_path=Path(temp_dir) / "events.log")
            tracker = EventTracker(config)
            assert tracker.config.log_path == Path(temp_dir) / "events.log"

    @patch('src.capture.event_tracker.win32gui')
    def test_active_window_title(self, mock_win32gui):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = EventTrackerConfig(log_path=Path(temp_dir) / "events.log")
            tracker = EventTracker(config)
            
            mock_win32gui.GetForegroundWindow.return_value = 123
            mock_win32gui.GetWindowText.return_value = "Test Window"
            
            title = tracker._active_window_title()
            assert title == "Test Window"

    def test_log_event(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = EventTrackerConfig(log_path=Path(temp_dir) / "events.log")
            tracker = EventTracker(config)
            
            tracker._log("test_event", {"key": "value"})
            
            # Check if log file was created and contains the event
            assert config.log_path.exists()
            content = config.log_path.read_text()
            assert "test_event" in content
            assert "key" in content
