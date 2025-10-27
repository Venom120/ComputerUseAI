import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.automation.computer_use import ComputerUse, ComputerUseConfig
from src.automation.executor import WorkflowExecutor, WorkflowStep, ExecutionResult
from src.automation.verification import ActionVerifier


class TestComputerUse:
    def test_initialization(self):
        config = ComputerUseConfig(click_delay=0.2, type_delay=0.1)
        computer_use = ComputerUse(config)
        assert computer_use.config.click_delay == 0.2
        assert computer_use.config.type_delay == 0.1

    @patch('src.automation.computer_use.pyautogui.click')
    def test_click_at_position(self, mock_click):
        config = ComputerUseConfig()
        computer_use = ComputerUse(config)
        
        result = computer_use.click_at_position(100, 200)
        
        assert result is True
        mock_click.assert_called_once_with(100, 200, button="left")

    @patch('src.automation.computer_use.pyautogui.typewrite')
    def test_type_text(self, mock_typewrite):
        config = ComputerUseConfig()
        computer_use = ComputerUse(config)
        
        result = computer_use.type_text("Hello World")
        
        assert result is True
        mock_typewrite.assert_called_once_with("Hello World", interval=0.05)

    @patch('src.automation.computer_use.pyautogui.press')
    def test_press_key(self, mock_press):
        config = ComputerUseConfig()
        computer_use = ComputerUse(config)
        
        result = computer_use.press_key("enter")
        
        assert result is True
        mock_press.assert_called_once_with("enter")

    @patch('src.automation.computer_use.pyautogui.hotkey')
    def test_press_key_combination(self, mock_hotkey):
        config = ComputerUseConfig()
        computer_use = ComputerUse(config)
        
        result = computer_use.press_key_combination(["ctrl", "c"])
        
        assert result is True
        mock_hotkey.assert_called_once_with("ctrl", "c")

    @patch('src.automation.computer_use.pyautogui.scroll')
    def test_scroll(self, mock_scroll):
        config = ComputerUseConfig()
        computer_use = ComputerUse(config)
        
        result = computer_use.scroll(3)
        
        assert result is True
        mock_scroll.assert_called_once_with(3)

    @patch('src.automation.computer_use.pyautogui.screenshot')
    def test_get_screen_region(self, mock_screenshot):
        config = ComputerUseConfig()
        computer_use = ComputerUse(config)
        
        mock_screenshot.return_value = Mock()
        result = computer_use.get_screen_region(10, 20, 100, 200)
        
        assert result is not None
        mock_screenshot.assert_called_once_with(region=(10, 20, 100, 200))

    @patch('src.automation.computer_use.pyautogui.locateOnScreen')
    @patch('src.automation.computer_use.pyautogui.center')
    def test_find_image_on_screen(self, mock_center, mock_locate):
        config = ComputerUseConfig()
        computer_use = ComputerUse(config)
        
        mock_location = Mock()
        mock_locate.return_value = mock_location
        mock_center.return_value = Mock(x=100, y=200)
        
        result = computer_use.find_image_on_screen("test.png")
        
        assert result == (100, 200)
        mock_locate.assert_called_once_with("test.png", confidence=0.8)


class TestWorkflowExecutor:
    def test_initialization(self):
        executor = WorkflowExecutor()
        assert executor._running is False

    def test_load_workflow(self):
        executor = WorkflowExecutor()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            workflow_data = {
                "steps": [
                    {
                        "action_type": "click",
                        "target": {"x": 100, "y": 200},
                        "verification": "window_change",
                        "retry_count": 2,
                        "timeout": 5
                    },
                    {
                        "action_type": "type",
                        "target": "Hello World",
                        "verification": "text_input",
                        "retry_count": 1,
                        "timeout": 3
                    }
                ]
            }
            import json
            json.dump(workflow_data, f)
            f.flush()
            
            steps = executor.load_workflow(f.name)
            
            assert len(steps) == 2
            assert steps[0].action_type == "click"
            assert steps[0].target == {"x": 100, "y": 200}
            assert steps[1].action_type == "type"
            assert steps[1].target == "Hello World"

    def test_load_workflow_invalid_file(self):
        executor = WorkflowExecutor()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json")
            f.flush()
            
            steps = executor.load_workflow(f.name)
            assert len(steps) == 0

    @patch('src.automation.executor.ComputerUse')
    def test_execute_workflow(self, mock_computer_use_class):
        executor = WorkflowExecutor()
        mock_computer_use = Mock()
        mock_computer_use_class.return_value = mock_computer_use
        
        steps = [
            WorkflowStep("click", {"x": 100, "y": 200}, "window_change"),
            WorkflowStep("type", "Hello", "text_input")
        ]
        
        result = executor.execute_workflow("test_workflow", steps)
        
        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert result.steps_completed == 2

    def test_execute_step_click(self):
        executor = WorkflowExecutor()
        step = WorkflowStep("click", {"x": 100, "y": 200}, "window_change")
        
        with patch.object(executor.computer_use, 'click_at_position', return_value=True):
            result = executor.execute_step(step, {})
            assert result is True

    def test_execute_step_type(self):
        executor = WorkflowExecutor()
        step = WorkflowStep("type", "Hello World", "text_input")
        
        with patch.object(executor.computer_use, 'type_text', return_value=True):
            result = executor.execute_step(step, {})
            assert result is True

    def test_execute_step_wait(self):
        executor = WorkflowExecutor()
        step = WorkflowStep("wait", 0.1, "none")
        
        result = executor.execute_step(step, {})
        assert result is True

    def test_stop_execution(self):
        executor = WorkflowExecutor()
        executor._running = True
        executor.stop_execution()
        assert executor._running is False

    def test_is_running(self):
        executor = WorkflowExecutor()
        assert executor.is_running() is False
        
        executor._running = True
        assert executor.is_running() is True


class TestActionVerifier:
    def test_initialization(self):
        verifier = ActionVerifier()
        assert verifier.ocr is not None

    @patch('src.automation.verification.pyautogui.screenshot')
    @patch('src.automation.verification.OCREngine.extract')
    def test_verify_click_success(self, mock_ocr_extract, mock_screenshot):
        verifier = ActionVerifier()
        
        mock_screenshot.return_value = Mock()
        mock_ocr_extract.return_value = {
            "items": [{"text": "Save Button", "conf": 90}]
        }
        
        with patch('builtins.open', Mock()), \
             patch('os.remove', Mock()):
            result = verifier.verify_click_success("Save")
            assert result is True

    @patch('src.automation.verification.win32gui')
    def test_verify_window_change(self, mock_win32gui):
        verifier = ActionVerifier()
        
        mock_win32gui.GetForegroundWindow.return_value = 123
        mock_win32gui.GetWindowText.return_value = "Excel - Workbook1"
        
        result = verifier.verify_window_change("Excel")
        assert result is True

    def test_get_verification_result_click_success(self):
        verifier = ActionVerifier()
        
        with patch.object(verifier, 'verify_click_success', return_value=True):
            result = verifier.get_verification_result(
                "click_success", 
                expected_text="Save"
            )
            assert result is True

    def test_get_verification_result_unknown_type(self):
        verifier = ActionVerifier()
        
        result = verifier.get_verification_result("unknown_type")
        assert result is True  # Should default to True for unknown types
