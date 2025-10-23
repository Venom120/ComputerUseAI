import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

from src.storage.database import initialize_database, Capture, Workflow, Event
from src.storage.file_manager import FileManager
from src.storage.cleanup import cleanup_old_files, cleanup_size_limit
from src.intelligence.llm_interface import LocalLLM, LLMConfig
from src.intelligence.workflow_generator import generate_automation_plan


class TestDatabaseIntegration:
    def test_initialize_database(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            session_factory = initialize_database(db_path)
            assert session_factory is not None
            
            # Test that we can create a session
            session = session_factory()
            assert session is not None
            session.close()
            
        finally:
            Path(db_path).unlink(missing_ok=True)

    def test_capture_model(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            session_factory = initialize_database(db_path)
            session = session_factory()
            
            # Create a capture record
            capture = Capture(
                type="screen",
                file_path="test.png",
                size_bytes=1024,
                metadata_json={"quality": 75}
            )
            
            session.add(capture)
            session.commit()
            
            # Query the record
            result = session.query(Capture).first()
            assert result.type == "screen"
            assert result.file_path == "test.png"
            assert result.size_bytes == 1024
            assert result.metadata_json["quality"] == 75
            
            session.close()
            
        finally:
            Path(db_path).unlink(missing_ok=True)

    def test_workflow_model(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            session_factory = initialize_database(db_path)
            session = session_factory()
            
            # Create a workflow record
            workflow = Workflow(
                name="test_workflow",
                description="Test workflow for data entry",
                pattern_json={"steps": [{"action": "click"}]},
                success_rate=0.95
            )
            
            session.add(workflow)
            session.commit()
            
            # Query the record
            result = session.query(Workflow).first()
            assert result.name == "test_workflow"
            assert result.description == "Test workflow for data entry"
            assert result.success_rate == 0.95
            assert result.pattern_json["steps"][0]["action"] == "click"
            
            session.close()
            
        finally:
            Path(db_path).unlink(missing_ok=True)


class TestFileManagerIntegration:
    def test_store_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_manager = FileManager()
            
            # Create a test file
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Hello World")
            
            # Store the file
            stored_path = file_manager.store(test_file, Path(temp_dir) / "stored")
            
            assert stored_path.exists()
            assert stored_path.read_text() == "Hello World"

    def test_total_size(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_manager = FileManager()
            
            # Create test files
            (Path(temp_dir) / "file1.txt").write_text("a" * 100)
            (Path(temp_dir) / "file2.txt").write_text("b" * 200)
            
            total_size = file_manager.total_size(temp_dir)
            assert total_size == 300

    def test_delete_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_manager = FileManager()
            
            # Create a test file
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Hello World")
            assert test_file.exists()
            
            # Delete the file
            file_manager.delete(test_file)
            assert not test_file.exists()


class TestCleanupIntegration:
    def test_cleanup_old_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            old_file = Path(temp_dir) / "old.txt"
            new_file = Path(temp_dir) / "new.txt"
            
            old_file.write_text("old content")
            new_file.write_text("new content")
            
            # Make old_file actually old
            import time
            old_time = time.time() - 10 * 24 * 3600  # 10 days ago
            old_file.touch()
            import os
            os.utime(old_file, (old_time, old_time))
            
            # Run cleanup
            removed = cleanup_old_files([temp_dir], max_age_days=7)
            
            assert removed == 1
            assert not old_file.exists()
            assert new_file.exists()

    def test_cleanup_size_limit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files with different sizes
            file1 = Path(temp_dir) / "file1.txt"
            file2 = Path(temp_dir) / "file2.txt"
            file3 = Path(temp_dir) / "file3.txt"
            
            file1.write_text("a" * 100)  # 100 bytes
            file2.write_text("b" * 200)  # 200 bytes
            file3.write_text("c" * 300)  # 300 bytes
            
            # Total size is 600 bytes, limit to 400 bytes
            removed = cleanup_size_limit(temp_dir, max_bytes=400)
            
            # Should remove the oldest files (file1 and file2)
            assert removed == 2
            assert not file1.exists()
            assert not file2.exists()
            assert file3.exists()


class TestLLMIntegration:
    @patch('src.intelligence.llm_interface.AutoTokenizer')
    @patch('src.intelligence.llm_interface.AutoModelForCausalLM')
    def test_llm_initialization(self, mock_model, mock_tokenizer):
        config = LLMConfig()
        
        # Mock the transformers components
        mock_tokenizer_instance = Mock()
        mock_tokenizer_instance.pad_token = None
        mock_tokenizer_instance.eos_token = "<eos>"
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance
        
        mock_model_instance = Mock()
        mock_model.from_pretrained.return_value = mock_model_instance
        
        llm = LocalLLM(config)
        
        assert llm._llm is not None
        assert "tokenizer" in llm._llm
        assert "model" in llm._llm

    def test_analyze_workflow_no_llm(self):
        config = LLMConfig()
        llm = LocalLLM(config)
        llm._llm = None  # Simulate no LLM loaded
        
        screen_jsons = [{"application": "Excel", "visible_text": ["Save"]}]
        transcripts = ["save the file"]
        events = [{"event_type": "click", "details": {"x": 100, "y": 200}}]
        
        result = llm.analyze_workflow(screen_jsons, transcripts, events)
        
        assert result["workflow_summary"] == ""
        assert result["steps"] == []
        assert result["is_repetitive"] is False
        assert result["automation_potential"] == "low"

    def test_build_prompt(self):
        config = LLMConfig()
        llm = LocalLLM(config)
        
        screen_jsons = [{"application": "Excel"}]
        transcripts = ["save file"]
        events = [{"event_type": "click"}]
        
        prompt = llm._build_prompt(screen_jsons, transcripts, events)
        
        assert "Screen States:" in prompt
        assert "Audio Commands:" in prompt
        assert "Event Log:" in prompt
        assert "workflow_summary" in prompt

    def test_safe_json_parsing(self):
        config = LLMConfig()
        llm = LocalLLM(config)
        
        # Test valid JSON
        valid_json = '{"workflow_summary": "Test", "steps": []}'
        result = llm._safe_json(valid_json)
        assert result["workflow_summary"] == "Test"
        
        # Test invalid JSON
        invalid_json = "not json"
        result = llm._safe_json(invalid_json)
        assert result["workflow_summary"] == "not json"


class TestWorkflowGeneratorIntegration:
    def test_generate_automation_plan(self):
        workflow_description = {
            "steps": [
                {"action": "click", "target": "Save button"},
                {"action": "type", "target": "filename.txt"},
                {"action": "key", "target": "enter"}
            ]
        }
        
        plan = generate_automation_plan(workflow_description)
        
        assert len(plan) == 3
        assert plan[0]["action_type"] == "click"
        assert plan[0]["target"] == "Save button"
        assert plan[1]["action_type"] == "type"
        assert plan[2]["action_type"] == "key"

    def test_generate_automation_plan_empty(self):
        workflow_description = {"steps": []}
        
        plan = generate_automation_plan(workflow_description)
        
        assert len(plan) == 0

    def test_generate_automation_plan_no_steps(self):
        workflow_description = {}
        
        plan = generate_automation_plan(workflow_description)
        
        assert len(plan) == 0


class TestEndToEndIntegration:
    @patch('src.capture.screen_capture.mss.mss')
    @patch('src.capture.audio_capture.sd.InputStream')
    def test_capture_to_processing_pipeline(self, mock_audio_stream, mock_mss):
        """Test the complete pipeline from capture to processing"""
        
        # Mock screen capture
        mock_sct = Mock()
        mock_sct.monitors = [{"top": 0, "left": 0, "width": 1920, "height": 1080}]
        mock_sct.grab.return_value = Mock()
        mock_mss.return_value = mock_sct
        
        # Mock audio stream
        mock_stream = Mock()
        mock_audio_stream.return_value = mock_stream
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # This would be a more comprehensive test in a real scenario
            # For now, we'll just verify the components can be imported and initialized
            from src.capture.screen_capture import ScreenCapture, ScreenCaptureConfig
            from src.capture.audio_capture import AudioCapture, AudioCaptureConfig
            from src.processing.speech_to_text import SpeechToText, STTConfig
            from src.processing.ocr_engine import OCREngine, OCRConfig
            
            # Initialize components
            screen_config = ScreenCaptureConfig()
            screen_capture = ScreenCapture(temp_dir, screen_config)
            
            audio_config = AudioCaptureConfig()
            audio_capture = AudioCapture(temp_dir, audio_config)
            
            stt_config = STTConfig()
            stt = SpeechToText(stt_config)
            
            ocr_config = OCRConfig()
            ocr = OCREngine(ocr_config)
            
            # Verify components are initialized
            assert screen_capture is not None
            assert audio_capture is not None
            assert stt is not None
            assert ocr is not None
