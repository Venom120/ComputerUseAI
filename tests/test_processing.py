import numpy as np
import numpy.testing
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.processing.speech_to_text import SpeechToText, STTConfig
from src.processing.ocr_engine import OCREngine, OCRConfig
from src.processing.screen_analyzer import ScreenAnalyzer, ScreenAnalyzerConfig
from src.processing.pattern_recognition import (
    extract_workflow_signature,
    calculate_similarity,
    detect_repetitive_patterns
)


class TestSpeechToText:
    def test_initialization(self):
        config = STTConfig(model_path=Path("base")) # Use a valid model name
        stt = SpeechToText(config)
        assert stt.config.model_path == Path("base")

    @patch('src.processing.speech_to_text.sf.read')
    @patch('src.processing.speech_to_text.SpeechToText._init_engine')
    def test_transcribe_file_faster_whisper(self, mock_init_engine, mock_sf_read):
        config = STTConfig(engine="faster-whisper", model_path=Path("base"))
        stt = SpeechToText(config)
        
        # Ensure _init_engine is called but doesn't actually initialize the engine
        mock_init_engine.assert_called_once()
        
        # Manually set a mock engine
        mock_engine_instance = Mock()
        stt._engine = mock_engine_instance
        
        # Mock soundfile.read
        mock_sf_read.return_value = (np.zeros(16000, dtype=np.float32), 16000) # 1 second of silent audio
        
        mock_engine_instance.transcribe.return_value = (
            [
                Mock(start=0.0, end=1.0, text="Hello world"),
                Mock(start=1.0, end=2.0, text="How are you")
            ],
            Mock(language_probability=0.9) # Mock info object
        )
        
        with tempfile.NamedTemporaryFile(suffix=".wav") as temp_file:
            result = stt.transcribe_file(temp_file.name)
            
            assert result["text"] == "Hello world How are you"
            assert len(result["timestamps"]) == 2
            assert result["confidence"] == 0.9 # Check against mocked confidence
            mock_sf_read.assert_called_once()
            # Verify transcribe was called once
            mock_engine_instance.transcribe.assert_called_once()
            
            # Get the actual argument passed to transcribe
            actual_audio_data = mock_engine_instance.transcribe.call_args.args[0]
            
            # Assert properties of the numpy array
            assert isinstance(actual_audio_data, np.ndarray)
            assert actual_audio_data.shape == (16000,)
            assert actual_audio_data.dtype == np.float32
            # Assert content using numpy.testing.assert_array_equal
            np.testing.assert_array_equal(actual_audio_data, np.zeros(16000, dtype=np.float32))

    def test_transcribe_file_no_engine(self):
        config = STTConfig()
        stt = SpeechToText(config)
        stt._engine = None
        
        with tempfile.NamedTemporaryFile(suffix=".wav") as temp_file:
            result = stt.transcribe_file(temp_file.name)
            
            assert result["text"] == ""
            assert result["confidence"] == 0.0
            assert result["timestamps"] == []


class TestOCREngine:
    def test_initialization(self):
        config = OCRConfig(language="eng")
        ocr = OCREngine(config)
        assert ocr.config.language == "eng"

    @patch('src.processing.ocr_engine.pytesseract.image_to_data')
    @patch('src.processing.ocr_engine.Image.open')
    def test_extract_text(self, mock_image_open, mock_image_to_data):
        config = OCRConfig()
        ocr = OCREngine(config)
        
        # Mock pytesseract response
        mock_image_to_data.return_value = {
            "text": ["Hello", "World", ""],
            "conf": [85, 90, -1],
            "left": [10, 20, 0],
            "top": [10, 20, 0],
            "width": [50, 60, 0],
            "height": [20, 25, 0]
        }
        
        with tempfile.NamedTemporaryFile(suffix=".png") as temp_file:
            result = ocr.extract(temp_file.name)
            
            assert len(result["items"]) == 2  # Only items with confidence >= 60
            assert result["items"][0]["text"] == "Hello"
            assert result["items"][0]["conf"] == 85


class TestScreenAnalyzer:
    def test_initialization(self):
        config = ScreenAnalyzerConfig()
        analyzer = ScreenAnalyzer(config)
        assert analyzer.config is not None

    def test_generate_screen_json(self):
        config = ScreenAnalyzerConfig()
        analyzer = ScreenAnalyzer(config)
        
        ocr_data = {
            "items": [
                {"text": "Save", "conf": 90},
                {"text": "Cancel", "conf": 85}
            ]
        }
        
        result = analyzer.generate_screen_json(
            "screenshot.png",
            ocr_data,
            "TestApp",
            "Test Window"
        )
        
        assert result["application"] == "TestApp"
        assert result["window_title"] == "Test Window"
        assert "Save" in result["visible_text"]
        assert "Cancel" in result["visible_text"]


class TestPatternRecognition:
    def test_extract_workflow_signature(self):
        workflow = {
            "application": "Excel",
            "steps": [{"action": "click"}, {"action": "type"}],
            "workflow_summary": "Data entry task"
        }
        
        signature = extract_workflow_signature(workflow)
        assert "Excel" in signature
        assert "click" in signature
        assert "Data entry task" in signature

    def test_calculate_similarity(self):
        workflow1 = {
            "application": "Excel",
            "steps": [{"action": "click"}],
            "workflow_summary": "Data entry"
        }
        workflow2 = {
            "application": "Excel", 
            "steps": [{"action": "click"}],
            "workflow_summary": "Data entry"
        }
        
        similarity = calculate_similarity(workflow1, workflow2)
        assert similarity > 0.9  # Should be very similar

    def test_detect_repetitive_patterns(self):
        workflows = [
            {"application": "Excel", "steps": [{"action": "click"}], "workflow_summary": "Task 1"},
            {"application": "Excel", "steps": [{"action": "click"}], "workflow_summary": "Task 1"},
            {"application": "Excel", "steps": [{"action": "click"}], "workflow_summary": "Task 1"},
            {"application": "Word", "steps": [{"action": "type"}], "workflow_summary": "Task 2"},
        ]
        
        patterns = detect_repetitive_patterns(workflows, threshold=0.8)
        assert len(patterns) == 1  # Should detect one pattern
        assert patterns[0]["occurrences"] == 3
