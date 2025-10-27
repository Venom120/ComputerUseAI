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
from typing import Optional


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
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# This is the project root, passed from the build script
PROJECT_ROOT = r"{self.project_root.as_posix()}"

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        (os.path.join(PROJECT_ROOT, 'config'), 'config'),
        # (os.path.join(PROJECT_ROOT, 'models'), 'models'),
        (os.path.join(PROJECT_ROOT, 'tools'), 'tools'),
        (os.path.join(PROJECT_ROOT, 'assets'), 'assets'),
        (os.path.join(PROJECT_ROOT, 'data'), 'data'),
        (os.path.join(PROJECT_ROOT, 'migrations'), 'migrations'),
        (os.path.join(PROJECT_ROOT, 'src'), 'src'), # Include src for relative imports
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'mss',
        'sounddevice',
        'pytesseract',
        'sqlalchemy',
        'alembic', # Include alembic for migrations
        'alembic.config',
        'alembic.command',
        'alembic.script',
        'alembic.operations',
        'numpy'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'torch',
        'transformers',
        'faster_whisper',
    ],
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
    icon=os.path.join(PROJECT_ROOT, 'assets/icon.ico') if sys.platform == 'win32' else \
         os.path.join(PROJECT_ROOT, 'assets/icon.icns') if sys.platform == 'darwin' else \
         os.path.join(PROJECT_ROOT, 'assets/icon.png'),
)
'''
        
        spec_path = self.project_root / "ComputerUseAI.spec"
        print("--- Generated PyInstaller Spec Content ---")
        print(spec_content)
        print("----------------------------------------")
        spec_path.write_text(spec_content)
        return spec_path
    
    def build_executable(self, platform: Optional[str] = None):
        """Build executable using PyInstaller"""
        print(f"Building executable for {platform or 'current platform'}...")
        
        # Create spec file
        spec_file = self.create_spec_file()
        
        # Build command
        cmd = [sys.executable, "-m", "PyInstaller", str(spec_file)]
        
        # The --onefile and --windowed options are already in the spec file,
        # so we don't need to pass them again on the command line.
        # if platform:
        #     # Platform-specific options
        #     if platform == "windows":
        #         cmd.extend(["--onefile", "--windowed"])
        #     elif platform == "macos":
        #         cmd.extend(["--onefile", "--windowed"])
        #     elif platform == "linux":
        #         cmd.extend(["--onefile"])
        
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
OutFile "ComputerUseAI-Setup.exe"

!include MUI2.nsh

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

section "install"
    ; Request admin privileges for installation into Program Files
    RequestExecutionLevel admin
    setOutPath $INSTDIR
    file "dist\\ComputerUseAI.exe"
    
    createDirectory "$SMPROGRAMS\\${APPNAME}"
    createShortCut "$SMPROGRAMS\\${APPNAME}\\${APPNAME}.lnk" "$INSTDIR\\ComputerUseAI.exe"
    createShortCut "$DESKTOP\\${APPNAME}.lnk" "$INSTDIR\\ComputerUseAI.exe"
    
    ; Add an option for the user to choose whether to create a desktop shortcut
    ; This requires a custom page or a checkbox on an existing page.
    ; For simplicity, I'll keep it as always creating for now, but this is where
    ; more advanced NSIS scripting would go.
    
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
        """Create macOS installer script (DMG with instructions)"""
        script = f'''#!/bin/bash
# macOS installer script for ComputerUseAI

APP_NAME="ComputerUseAI"
APP_VERSION="1.0.0"
DMG_NAME="${{APP_NAME}}-${{APP_VERSION}}.dmg"
VOLUME_NAME="${{APP_NAME}} Installer"
APP_BUNDLE_NAME="${{APP_NAME}}.app"

echo "Creating macOS Disk Image for ${{APP_NAME}}..."

# Ensure dist/{{APP_BUNDLE_NAME}} exists
if [ ! -d "dist/${{APP_BUNDLE_NAME}}" ]; then
    echo "Error: dist/${{APP_BUNDLE_NAME}} not found. Please build the macOS executable first."
    exit 1
fi

# Create a temporary directory for DMG contents
TMP_DIR=$(mktemp -d)
mkdir -p "${{TMP_DIR}}/${{VOLUME_NAME}}"
cp -r "dist/${{APP_BUNDLE_NAME}}" "${{TMP_DIR}}/${{VOLUME_NAME}}/"

# Add a symlink to Applications folder
ln -s /Applications "${{TMP_DIR}}/${{VOLUME_NAME}}/Applications"

# Create the DMG
hdiutil create -ov -fs HFS+ -srcfolder "${{TMP_DIR}}/${{VOLUME_NAME}}" -volname "${{VOLUME_NAME}}" "dist/${{DMG_NAME}}"

# Clean up temporary directory
rm -rf "${{TMP_DIR}}"

echo "Created dist/${{DMG_NAME}}. Please open the DMG and drag ${{APP_BUNDLE_NAME}} to your Applications folder."
echo "To create a desktop shortcut, drag the app from Applications to your Desktop."
'''
        script_path = self.project_root / "create_macos_dmg.sh"
        script_path.write_text(script)
        script_path.chmod(0o755)
        return script_path
    
    def _create_linux_installer(self):
        """Create Linux installer script (using a simple tar.gz and .desktop file)"""
        script = f'''#!/bin/bash
# Linux installer script for ComputerUseAI

APP_NAME="ComputerUseAI"
APP_VERSION="1.0.0"
INSTALL_DIR="/opt/${{APP_NAME}}"
DESKTOP_FILE_NAME="${{APP_NAME}}.desktop"
APP_EXECUTABLE="${{INSTALL_DIR}}/ComputerUseAI"

echo "Preparing to install ${{APP_NAME}} version ${{APP_VERSION}}..."

# Ask for installation directory
read -p "Enter installation directory (default: ${{INSTALL_DIR}}): " USER_INSTALL_DIR
if [ -n "$USER_INSTALL_DIR" ]; then
    INSTALL_DIR="$USER_INSTALL_DIR"
fi

echo "Installing to: ${{INSTALL_DIR}}"

# Create installation directory
sudo mkdir -p "${{INSTALL_DIR}}"
sudo cp -r dist/ComputerUseAI/* "${{INSTALL_DIR}}/"

# Create .desktop file for application menu and desktop shortcut
DESKTOP_CONTENT="[Desktop Entry]
Version=1.0
Type=Application
Name=${{APP_NAME}}
Comment=Desktop AI Assistant
Exec=${{APP_EXECUTABLE}}
Icon=${{INSTALL_DIR}}/assets/icon.png
Terminal=false
Categories=Utility;AI;
"

echo "${{DESKTOP_CONTENT}}" | sudo tee "/usr/share/applications/${{DESKTOP_FILE_NAME}}" > /dev/null

# Ask to create desktop shortcut
read -p "Create desktop shortcut? (y/N): " CREATE_SHORTCUT
if [[ "$CREATE_SHORTCUT" =~ ^[Yy]$ ]]; then
    cp "/usr/share/applications/${{DESKTOP_FILE_NAME}}" "${{HOME}}/Desktop/"
    chmod +x "${{HOME}}/Desktop/${{DESKTOP_FILE_NAME}}"
    echo "Desktop shortcut created."
fi

echo "Installation complete. You can find ${{APP_NAME}} in your applications menu."
'''
        script_path = self.project_root / "install_linux.sh"
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
