import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as temp_path:
        yield Path(temp_path)


@pytest.fixture
def sample_workflow():
    """Sample workflow data for testing"""
    return {
        "name": "test_workflow",
        "description": "Test workflow for automation",
        "steps": [
            {
                "action_type": "click",
                "target": {"x": 100, "y": 200},
                "verification": "window_change",
                "retry_count": 3,
                "timeout": 5
            },
            {
                "action_type": "type",
                "target": "Hello World",
                "verification": "text_input",
                "retry_count": 2,
                "timeout": 3
            },
            {
                "action_type": "key",
                "target": "enter",
                "verification": "none",
                "retry_count": 1,
                "timeout": 1
            }
        ]
    }


@pytest.fixture
def sample_screen_data():
    """Sample screen analysis data for testing"""
    return {
        "timestamp": "2025-01-23T14:30:00Z",
        "application": "Microsoft Excel",
        "window_title": "Workbook1.xlsx",
        "visible_text": ["Save", "Cancel", "File", "Edit"],
        "ui_elements": [
            {"type": "button", "text": "Save", "position": {"x": 50, "y": 20}},
            {"type": "button", "text": "Cancel", "position": {"x": 100, "y": 20}}
        ],
        "context": "User is working on a spreadsheet"
    }


@pytest.fixture
def sample_audio_data():
    """Sample audio transcription data for testing"""
    return {
        "text": "save the file and close the application",
        "confidence": 0.95,
        "timestamps": [
            {"start": 0.0, "end": 1.5, "text": "save the file"},
            {"start": 1.5, "end": 2.0, "text": "and close the application"}
        ]
    }


@pytest.fixture
def sample_events():
    """Sample event data for testing"""
    return [
        {
            "timestamp": "2025-01-23T14:30:00Z",
            "event_type": "mouse_click",
            "window": "Excel - Workbook1.xlsx",
            "app": "EXCEL.EXE",
            "details": {"x": 100, "y": 200, "button": "left"}
        },
        {
            "timestamp": "2025-01-23T14:30:01Z",
            "event_type": "key_press",
            "window": "Excel - Workbook1.xlsx",
            "app": "EXCEL.EXE",
            "details": {"key": "ctrl+s"}
        }
    ]


@pytest.fixture(autouse=True)
def mock_pyautogui():
    """Mock pyautogui for all tests to avoid actual system interactions"""
    import sys
    from unittest.mock import Mock
    
    mock_pyautogui = Mock()
    mock_pyautogui.click.return_value = None
    mock_pyautogui.typewrite.return_value = None
    mock_pyautogui.press.return_value = None
    mock_pyautogui.hotkey.return_value = None
    mock_pyautogui.scroll.return_value = None
    mock_pyautogui.screenshot.return_value = Mock()
    mock_pyautogui.locateOnScreen.return_value = None
    mock_pyautogui.center.return_value = Mock(x=100, y=200)
    
    sys.modules['pyautogui'] = mock_pyautogui
    yield mock_pyautogui


@pytest.fixture(autouse=True)
def mock_win32gui():
    """Mock win32gui for Windows-specific tests"""
    import sys
    from unittest.mock import Mock
    
    mock_win32gui = Mock()
    mock_win32gui.GetForegroundWindow.return_value = 123
    mock_win32gui.GetWindowText.return_value = "Test Window"
    mock_win32gui.GetWindowThreadProcessId.return_value = (456, 789)
    
    sys.modules['win32gui'] = mock_win32gui
    sys.modules['win32process'] = Mock()
    yield mock_win32gui
