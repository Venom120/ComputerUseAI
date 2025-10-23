#!/usr/bin/env python3
"""
Setup script for ComputerUseAI
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    with requirements_path.open() as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="ComputerUseAI",
    version="1.0.0",
    author="ComputerUseAI Team",
    author_email="contact@computeruseai.com",
    description="Desktop AI Assistant for Workflow Automation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ComputerUseAI/ComputerUseAI",
    project_urls={
        "Bug Reports": "https://github.com/ComputerUseAI/ComputerUseAI/issues",
        "Source": "https://github.com/ComputerUseAI/ComputerUseAI",
        "Documentation": "https://github.com/ComputerUseAI/ComputerUseAI/wiki",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Desktop Environment",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ],
        "build": [
            "pyinstaller>=6.0.0",
            "cx_Freeze>=6.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "computeruseai=src.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["config/*.json", "models/*.bin", "models/*.gguf"],
    },
    data_files=[
        ("config", ["config/settings.json"]),
        ("models", []),  # Models will be downloaded by model_setup.py
    ],
    keywords=[
        "ai", "automation", "desktop", "workflow", "assistant", 
        "computer-vision", "speech-recognition", "machine-learning"
    ],
    zip_safe=False,
)
