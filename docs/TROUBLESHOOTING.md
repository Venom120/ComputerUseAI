# ComputerUseAI Troubleshooting Guide

## Quick Diagnostics

### System Check
```bash
# Check Python version
python --version

# Check dependencies
pip list | grep -E "(PyQt6|opencv|mss|sounddevice)"

# Check Tesseract
tesseract --version

# Check system resources
python -c "import psutil; print(f'RAM: {psutil.virtual_memory().total // (1024**3)}GB')"
```

### Application Health
```bash
# Check logs
tail -f data/logs/computeruseai.log

# Test model loading
python -c "from src.intelligence.llm_interface import LocalLLM; print('LLM OK')"

# Test capture
python -c "from src.capture.screen_capture import ScreenCapture; print('Capture OK')"
```

## Common Issues & Solutions

### Installation Problems

#### Issue: "ModuleNotFoundError" during installation
**Symptoms**: Missing dependencies, import errors
**Solutions**:
```bash
# Update pip
python -m pip install --upgrade pip

# Install with verbose output
pip install -r requirements.txt -v

# Install system dependencies
# Windows: Install Visual C++ Build Tools
# macOS: xcode-select --install
# Linux: sudo apt install build-essential
```

#### Issue: Tesseract not found
**Symptoms**: OCR errors, "tesseract not found"
**Solutions**:
```bash
# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Add to PATH: C:\Program Files\Tesseract-OCR

# macOS
brew install tesseract

# Linux
sudo apt install tesseract-ocr
sudo apt install libtesseract-dev
```

#### Issue: PyQt6 installation fails
**Symptoms**: GUI won't start, PyQt6 errors
**Solutions**:
```bash
# Try different installation method
pip install PyQt6 --no-cache-dir

# Or use conda
conda install pyqt

# Or install system packages
# Ubuntu: sudo apt install python3-pyqt6
# macOS: brew install pyqt6
```

### Runtime Issues

#### Issue: Application won't start
**Symptoms**: Crashes on startup, blank window
**Solutions**:
```bash
# Check system tray availability
python -c "from PyQt6.QtWidgets import QSystemTrayIcon; print(QSystemTrayIcon.isSystemTrayAvailable())"

# Run with debug output
python -m src.main --debug

# Check permissions
# Windows: Run as administrator
# macOS: Grant accessibility permissions
# Linux: Check X11/Wayland compatibility
```

#### Issue: Screen capture fails
**Symptoms**: Black screenshots, permission errors
**Solutions**:
```bash
# Check screen recording permissions
# macOS: System Preferences > Security & Privacy > Screen Recording
# Windows: Check antivirus settings
# Linux: Check X11 permissions

# Test capture manually
python -c "
import mss
with mss.mss() as sct:
    screenshot = sct.grab(sct.monitors[0])
    print('Capture OK')
"
```

#### Issue: Audio capture fails
**Symptoms**: No audio recorded, microphone errors
**Solutions**:
```bash
# Check audio permissions
# macOS: System Preferences > Security & Privacy > Microphone
# Windows: Check microphone privacy settings
# Linux: Check ALSA/PulseAudio

# Test audio devices
python -c "
import sounddevice as sd
print('Audio devices:', sd.query_devices())
"
```

### Performance Issues

#### Issue: High CPU usage
**Symptoms**: System slowdown, fan noise
**Solutions**:
```bash
# Reduce capture settings
# Settings > Capture > FPS: 2, Quality: 60%

# Disable unnecessary features
# Settings > Processing > Disable real-time analysis

# Check for background processes
# Task Manager / Activity Monitor
```

#### Issue: High memory usage
**Symptoms**: System slowdown, out of memory errors
**Solutions**:
```bash
# Reduce model size
# Use smaller LLM model (TinyLlama instead of Phi-3)

# Increase cleanup frequency
# Settings > Storage > Cleanup: Daily

# Check memory usage
python -c "
import psutil
print(f'Memory: {psutil.virtual_memory().percent}%')
"
```

#### Issue: Slow processing
**Symptoms**: Delayed workflow detection, slow automation
**Solutions**:
```bash
# Use faster models
# Settings > AI > Model: TinyLlama

# Reduce processing quality
# Settings > Processing > Quality: Medium

# Enable GPU acceleration (if available)
# Install CUDA/OpenCL drivers
```

### Automation Issues

#### Issue: Workflows not detected
**Symptoms**: No workflows learned, empty workflow list
**Solutions**:
```bash
# Increase recording time
# Record for at least 10-15 minutes

# Perform tasks more consistently
# Use same applications and patterns

# Check confidence threshold
# Settings > Automation > Threshold: 70%

# Review privacy settings
# Ensure applications aren't excluded
```

#### Issue: Automation fails
**Symptoms**: Workflows don't execute, error messages
**Solutions**:
```bash
# Check application permissions
# Grant accessibility permissions

# Test workflows manually
# Workflows tab > Select workflow > Run

# Check UI changes
# Applications may have updated interfaces

# Review error logs
# Automation tab > View execution log
```

#### Issue: Inaccurate automation
**Symptoms**: Wrong actions, missed steps
**Solutions**:
```bash
# Adjust confidence threshold
# Settings > Automation > Threshold: 85%

# Update workflow steps
# Workflows tab > Edit workflow

# Provide feedback
# Mark successful/failed executions

# Retrain with better examples
# Record more consistent patterns
```

### Data Issues

#### Issue: Storage full
**Symptoms**: "Storage limit reached" messages
**Solutions**:
```bash
# Clean old data
# Settings > Storage > Cleanup now

# Increase storage limit
# Settings > Storage > Limit: 2GB

# Export important data
# Timeline tab > Export data

# Check disk space
df -h  # Linux/macOS
dir C:\  # Windows
```

#### Issue: Data corruption
**Symptoms**: Application crashes, missing data
**Solutions**:
```bash
# Backup current data
cp -r data/ data_backup/

# Reset database
rm data/app.db
# Application will recreate on next start

# Check file integrity
python -c "
import sqlite3
conn = sqlite3.connect('data/app.db')
conn.execute('PRAGMA integrity_check')
"
```

#### Issue: Models not loading
**Symptoms**: "Model not found" errors
**Solutions**:
```bash
# Re-download models
python tools/model_setup.py

# Check model files
ls -la models/

# Verify model integrity
python -c "
from pathlib import Path
models = Path('models')
for model in models.glob('*.bin'):
    print(f'{model}: {model.stat().st_size} bytes')
"
```

## Platform-Specific Issues

### Windows

#### Issue: Antivirus blocking
**Solutions**:
- Add application to antivirus exclusions
- Disable real-time protection temporarily
- Use Windows Defender exclusions

#### Issue: UAC prompts
**Solutions**:
- Run as administrator
- Disable UAC for development
- Use elevated command prompt

#### Issue: PyWin32 errors
**Solutions**:
```bash
# Reinstall pywin32
pip uninstall pywin32
pip install pywin32

# Or use conda
conda install pywin32
```

### macOS

#### Issue: Code signing errors
**Solutions**:
- Disable Gatekeeper: `sudo spctl --master-disable`
- Allow unsigned applications
- Use developer certificate

#### Issue: Accessibility permissions
**Solutions**:
- System Preferences > Security & Privacy > Accessibility
- Add ComputerUseAI to allowed applications
- Restart application after granting permissions

#### Issue: Homebrew conflicts
**Solutions**:
```bash
# Update Homebrew
brew update && brew upgrade

# Reinstall dependencies
brew reinstall tesseract
```

### Linux

#### Issue: X11/Wayland compatibility
**Solutions**:
```bash
# Check display server
echo $XDG_SESSION_TYPE

# For Wayland, use XWayland
export GDK_BACKEND=x11

# Install X11 dependencies
sudo apt install python3-tk python3-dev
```

#### Issue: Audio system conflicts
**Solutions**:
```bash
# Check audio system
pactl info  # PulseAudio
arecord -l  # ALSA

# Install audio dependencies
sudo apt install libasound2-dev portaudio19-dev
```

## Advanced Troubleshooting

### Debug Mode

```bash
# Enable debug logging
export COMPUTERUSEAI_DEBUG=1
python -m src.main

# Or use command line
python -m src.main --debug --verbose
```

### Performance Profiling

```bash
# Profile CPU usage
python -m cProfile -o profile.stats -m src.main

# Analyze profile
python -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative').print_stats(10)
"
```

### Memory Analysis

```bash
# Check memory usage
python -c "
import tracemalloc
tracemalloc.start()
# Run application
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
"
```

### Network Diagnostics

```bash
# Check model downloads
curl -I https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin

# Test connectivity
ping huggingface.co

# Check DNS resolution
nslookup huggingface.co
```

## Getting Help

### Log Files

**Location**: `data/logs/computeruseai.log`

**Key Information**:
- Error messages and stack traces
- Performance metrics
- User actions and system events
- Debug information

**Log Levels**:
- DEBUG: Detailed debugging information
- INFO: General application flow
- WARNING: Potential issues
- ERROR: Error conditions
- CRITICAL: Application-stopping errors

### System Information

**Collect for Support**:
```bash
# System info
python -c "
import platform, sys, psutil
print(f'OS: {platform.system()} {platform.release()}')
print(f'Python: {sys.version}')
print(f'RAM: {psutil.virtual_memory().total // (1024**3)}GB')
print(f'CPU: {psutil.cpu_count()} cores')
"

# Application info
python -c "
import src
print(f'Version: {src.__version__}')
print(f'Path: {src.__file__}')
"

# Dependencies
pip list | grep -E "(PyQt6|opencv|mss|sounddevice|transformers)"
```

### Reporting Issues

**Include**:
1. Operating system and version
2. Python version
3. Error messages and stack traces
4. Steps to reproduce
5. Expected vs actual behavior
6. Log files (sanitized)
7. System specifications

**GitHub Issues**:
- Use issue templates
- Attach relevant files
- Include system information
- Provide reproduction steps

### Community Support

**Resources**:
- GitHub Discussions
- Discord/Slack channels
- Stack Overflow (tag: computeruseai)
- Reddit communities
- User forums

**Best Practices**:
- Search existing issues first
- Provide detailed information
- Be patient with responses
- Contribute back to community
