from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

# Ensure project root is on sys.path to import src.* when executed as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import tesseract_installed


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url) as r, open(tmp, "wb") as f:
        f.write(r.read())
    tmp.replace(dest)


def setup_models() -> None:
    models_dir = Path("./models")
    models_dir.mkdir(exist_ok=True)

    whisper_model = models_dir / "whisper-base.bin"
    if not whisper_model.exists():
        print("Downloading Whisper model...")
        download_file(
            "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
            whisper_model,
        )

    llm_model = models_dir / "phi-3-mini-4k-instruct-q4.gguf"
    if not llm_model.exists():
        print("Downloading LLM model...")
        download_file(
            "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf",
            llm_model,
        )

    if not tesseract_installed():
        print("Please install Tesseract OCR:")
        print("  Windows: https://github.com/UB-Mannheim/tesseract/wiki")
        print("  macOS: brew install tesseract")
        print("  Linux: sudo apt install tesseract-ocr")


if __name__ == "__main__":
    setup_models()

