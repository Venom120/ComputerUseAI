# ComputerUseAI - Desktop AI Assistant

A privacy-first desktop AI assistant that observes your screen activity, learns your workflows, and automates repetitive tasks—all running locally on your system.

## 🚀 Features

- **Real-time Screen & Audio Capture** - Records your desktop activity with frame differencing optimization
- **Local Speech-to-Text** - Transcribes audio using Whisper.cpp (completely offline)
- **Computer Vision & OCR** - Understands screen content using Tesseract OCR
- **Pattern Recognition** - Learns your workflows using local LLM (Phi-3 Mini)
- **Task Automation** - Executes learned workflows automatically
- **Privacy-First Design** - All processing happens locally, no cloud dependencies
- **Cross-Platform** - Works on Windows, macOS, and Linux

## 📋 Requirements

- Python 3.8+
- 4GB+ RAM (8GB recommended for LLM)
- 2GB+ free disk space
- Tesseract OCR installed

## 🛠️ Installation

### Quick Start (Windows)

```powershell
# 1. Clone and setup
git clone https://github.com/ComputerUseAI/ComputerUseAI.git
cd ComputerUseAI
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Tesseract OCR
# Download from: https://github.com/UB-Mannheim/tesseract/wiki

# 4. Download AI models
python tools/model_setup.py

# 5. Run the application
python -m src.main
```

### Quick Start (macOS)

```bash
# 1. Install dependencies
brew install tesseract
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Download models and run
python tools/model_setup.py
python -m src.main
```

### Quick Start (Linux)

```bash
# 1. Install system dependencies
sudo apt install tesseract-ocr python3-venv

# 2. Setup Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Download models and run
python tools/model_setup.py
python -m src.main
```

## 🎯 Usage

### First Run

1. **Start the Application** - Run `python -m src.main`
2. **Grant Permissions** - Allow screen recording and microphone access when prompted
3. **Configure Settings** - Go to Settings tab to adjust capture quality, storage limits, and privacy settings
4. **Start Recording** - Click "Start Recording" to begin learning your workflows

### Learning Workflows

1. **Perform Your Task** - Do your repetitive task normally (e.g., data entry, file organization)
2. **Let It Learn** - The AI observes your actions and learns the pattern
3. **Review Detected Workflows** - Check the Workflows tab to see what it learned
4. **Enable Automation** - Turn on automation for workflows you want to automate

### Automation

1. **Enable Automation** - Go to Automation tab and check "Enable Automation"
2. **Set Confidence Threshold** - Adjust how confident the AI needs to be before automating
3. **Monitor Execution** - Watch the automation log to see what it's doing
4. **Intervene When Needed** - You can always stop or modify automation

## ⚙️ Configuration

### Settings

- **Capture Settings**: FPS, quality, storage limits
- **Privacy Settings**: Exclude specific applications from recording
- **Automation Settings**: Confidence thresholds, execution preferences

### Privacy Controls

- **Application Exclusion**: Blacklist sensitive applications (banking, messaging)
- **Local Processing**: All AI processing happens on your device
- **Data Encryption**: Optional encryption for stored data
- **Auto-Cleanup**: Automatic deletion of old recordings

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Capture       │    │   Processing     │    │   Intelligence   │
│                 │    │                 │    │                 │
│ • Screen        │───▶│ • Speech-to-Text │───▶│ • Local LLM     │
│ • Audio         │    │ • OCR            │    │ • Pattern Rec.  │
│ • Events        │    │ • Screen Analysis│    │ • Workflow Gen. │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Storage        │    │   Automation    │    │   User Interface│
│                 │    │                 │    │                 │
│ • SQLite DB     │    │ • Computer Use  │    │ • PyQt6 GUI     │
│ • File Manager  │    │ • Workflow Exec │    │ • System Tray   │
│ • Cleanup       │    │ • Verification  │    │ • Settings      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🧪 Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -e ".[dev,build]"

# Run tests
pytest tests/ -v

# Run linting
flake8 src/ tests/
mypy src/

# Format code
black src/ tests/
```

### Building Executables

```bash
# Build for current platform
python build.py

# Build for all platforms
python build.py --platform all

# Using Makefile
make build
```

## 📚 Documentation

- [Architecture Guide](docs/ARCHITECTURE.md) - Detailed system architecture
- [API Reference](docs/API.md) - Code documentation and APIs
- [User Guide](docs/USER_GUIDE.md) - Comprehensive user manual
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions

## 🔒 Privacy & Security

- **Local Processing**: All AI models run on your device
- **No Cloud Dependencies**: No data sent to external servers
- **Encrypted Storage**: Optional encryption for sensitive data
- **Application Exclusion**: Blacklist sensitive applications
- **Open Source**: Full source code available for audit

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Whisper.cpp](https://github.com/ggerganov/whisper.cpp) for speech recognition
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) for text extraction
- [Microsoft Phi-3](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf) for local LLM
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the GUI framework

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/ComputerUseAI/ComputerUseAI/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ComputerUseAI/ComputerUseAI/discussions)
- **Documentation**: [Wiki](https://github.com/ComputerUseAI/ComputerUseAI/wiki)

---

**ComputerUseAI** - Making your computer work smarter, not harder. 🤖✨