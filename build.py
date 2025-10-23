#!/usr/bin/env python3
"""
Build script for ComputerUseAI
Creates executable packages for Windows, macOS, and Linux
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any


class Builder:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        
    def clean(self):
        """Clean build and dist directories"""
        print("Cleaning build directories...")
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        print("✓ Cleaned build directories")
    
    def install_dependencies(self):
        """Install build dependencies"""
        print("Installing build dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("✓ Build dependencies installed")
    
    def create_spec_file(self) -> Path:
        """Create PyInstaller spec file"""
        spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('models', 'models'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'mss',
        'sounddevice',
        'pytesseract',
        'faster_whisper',
        'transformers',
        'sqlalchemy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ComputerUseAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
)
'''
        
        spec_path = self.project_root / "ComputerUseAI.spec"
        spec_path.write_text(spec_content)
        return spec_path
    
    def build_executable(self, platform: str = None):
        """Build executable using PyInstaller"""
        print(f"Building executable for {platform or 'current platform'}...")
        
        # Create spec file
        spec_file = self.create_spec_file()
        
        # Build command
        cmd = [sys.executable, "-m", "PyInstaller", str(spec_file)]
        
        if platform:
            # Platform-specific options
            if platform == "windows":
                cmd.extend(["--onefile", "--windowed"])
            elif platform == "macos":
                cmd.extend(["--onefile", "--windowed"])
            elif platform == "linux":
                cmd.extend(["--onefile"])
        
        # Run build
        result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Build failed: {result.stderr}")
            return False
        
        print("✓ Executable built successfully")
        return True
    
    def create_installer_script(self, platform: str):
        """Create installer script for the platform"""
        if platform == "windows":
            return self._create_windows_installer()
        elif platform == "macos":
            return self._create_macos_installer()
        elif platform == "linux":
            return self._create_linux_installer()
    
    def _create_windows_installer(self):
        """Create Windows installer using NSIS"""
        nsis_script = '''
!define APPNAME "ComputerUseAI"
!define COMPANYNAME "ComputerUseAI"
!define DESCRIPTION "Desktop AI Assistant"
!define VERSIONMAJOR 1
!define VERSIONMINOR 0
!define VERSIONBUILD 0

!define HELPURL "https://github.com/ComputerUseAI"
!define UPDATEURL "https://github.com/ComputerUseAI"
!define ABOUTURL "https://github.com/ComputerUseAI"

!define INSTALLSIZE 500000

RequestExecutionLevel admin
InstallDir "$PROGRAMFILES\\${APPNAME}"
Name "${APPNAME}"
outFile "ComputerUseAI-Setup.exe"

!include LogicLib.nsh

page directory
page instfiles

section "install"
    setOutPath $INSTDIR
    file "dist\\ComputerUseAI.exe"
    
    createDirectory "$SMPROGRAMS\\${APPNAME}"
    createShortCut "$SMPROGRAMS\\${APPNAME}\\${APPNAME}.lnk" "$INSTDIR\\ComputerUseAI.exe"
    createShortCut "$DESKTOP\\${APPNAME}.lnk" "$INSTDIR\\ComputerUseAI.exe"
    
    writeUninstaller "$INSTDIR\\uninstall.exe"
    
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "DisplayName" "${APPNAME}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "UninstallString" "$INSTDIR\\uninstall.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "DisplayIcon" "$INSTDIR\\ComputerUseAI.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "Publisher" "${COMPANYNAME}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "HelpLink" "${HELPURL}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "URLUpdateInfo" "${UPDATEURL}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "URLInfoAbout" "${ABOUTURL}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "DisplayVersion" "${VERSIONMAJOR}.${VERSIONMINOR}.${VERSIONBUILD}"
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "VersionMajor" ${VERSIONMAJOR}
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "VersionMinor" ${VERSIONMINOR}
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "NoModify" 1
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "NoRepair" 1
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "EstimatedSize" ${INSTALLSIZE}
sectionEnd

section "uninstall"
    delete "$INSTDIR\\ComputerUseAI.exe"
    delete "$INSTDIR\\uninstall.exe"
    rmDir "$INSTDIR"
    
    delete "$SMPROGRAMS\\${APPNAME}\\${APPNAME}.lnk"
    rmDir "$SMPROGRAMS\\${APPNAME}"
    delete "$DESKTOP\\${APPNAME}.lnk"
    
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}"
sectionEnd
'''
        
        script_path = self.project_root / "installer.nsi"
        script_path.write_text(nsis_script)
        return script_path
    
    def _create_macos_installer(self):
        """Create macOS installer script"""
        script = '''#!/bin/bash
# macOS installer script for ComputerUseAI

APP_NAME="ComputerUseAI"
APP_VERSION="1.0.0"
DMG_NAME="ComputerUseAI-${APP_VERSION}.dmg"
VOLUME_NAME="ComputerUseAI"

# Create DMG
hdiutil create -srcfolder "dist/ComputerUseAI.app" -volname "${VOLUME_NAME}" "${DMG_NAME}"

echo "Created ${DMG_NAME}"
'''
        
        script_path = self.project_root / "create_dmg.sh"
        script_path.write_text(script)
        script_path.chmod(0o755)
        return script_path
    
    def _create_linux_installer(self):
        """Create Linux AppImage script"""
        script = '''#!/bin/bash
# Linux AppImage creation script for ComputerUseAI

APP_NAME="ComputerUseAI"
APP_VERSION="1.0.0"
APPIMAGE_NAME="ComputerUseAI-${APP_VERSION}.AppImage"

# Create AppImage using appimagetool
if command -v appimagetool &> /dev/null; then
    appimagetool dist/ComputerUseAI.AppDir "${APPIMAGE_NAME}"
    echo "Created ${APPIMAGE_NAME}"
else
    echo "appimagetool not found. Please install it first."
    exit 1
fi
'''
        
        script_path = self.project_root / "create_appimage.sh"
        script_path.write_text(script)
        script_path.chmod(0o755)
        return script_path
    
    def create_launcher_script(self):
        """Create launcher script for development"""
        launcher_content = '''#!/usr/bin/env python3
"""
Development launcher for ComputerUseAI
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    from src.main import main
    sys.exit(main())
'''
        
        launcher_path = self.project_root / "run.py"
        launcher_path.write_text(launcher_content)
        launcher_path.chmod(0o755)
        return launcher_path
    
    def build_all(self):
        """Build for all platforms"""
        platforms = ["windows", "macos", "linux"]
        
        for platform in platforms:
            print(f"\n{'='*50}")
            print(f"Building for {platform.upper()}")
            print(f"{'='*50}")
            
            self.clean()
            self.install_dependencies()
            
            if self.build_executable(platform):
                installer_script = self.create_installer_script(platform)
                print(f"✓ Created installer script: {installer_script}")
            else:
                print(f"✗ Failed to build for {platform}")
    
    def build_current(self):
        """Build for current platform only"""
        print("Building for current platform...")
        self.clean()
        self.install_dependencies()
        
        if self.build_executable():
            print("✓ Build completed successfully")
            print(f"Executable location: {self.dist_dir}")
        else:
            print("✗ Build failed")
            return False
        
        return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Build ComputerUseAI")
    parser.add_argument("--platform", choices=["windows", "macos", "linux", "all"], 
                       default="current", help="Target platform")
    parser.add_argument("--clean", action="store_true", help="Clean build directories only")
    
    args = parser.parse_args()
    
    builder = Builder()
    
    if args.clean:
        builder.clean()
        return
    
    if args.platform == "all":
        builder.build_all()
    elif args.platform == "current":
        builder.build_current()
    else:
        builder.clean()
        builder.install_dependencies()
        builder.build_executable(args.platform)


if __name__ == "__main__":
    main()
