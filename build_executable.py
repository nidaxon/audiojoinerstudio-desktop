#!/usr/bin/env python3
"""
Automated PyInstaller Build Script for AudioJoiner Studio
Builds standalone desktop executables for Windows (.exe), macOS (.app), and Linux.
"""

import os
import sys
import shutil
import subprocess
import py_compile

APP_NAME = "AudioJoinerStudio"
ENTRY_POINT = "main.py"

def pre_check_syntax():
    """Verify that all source Python files have valid syntax before compiling."""
    files = ["main.py", "audio_engine.py", "playlist_parser.py", "styles.py"]
    print("[*] Validating source code syntax...")
    for f in files:
        if os.path.exists(f):
            try:
                py_compile.compile(f, doraise=True)
                print(f"  [✓] {f} passed syntax check.")
            except py_compile.PyCompileError as e:
                print(f"\n[!] Syntax Error detected in {f}:")
                print(f"    {e.msg}")
                sys.exit(1)

def build():
    print(f"[*] Starting build process for {APP_NAME} on {sys.platform}...")
    pre_check_syntax()

    # Ensure pyinstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("[!] PyInstaller is not installed. Installing via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        f"--name={APP_NAME}",
        ENTRY_POINT
    ]

    # Application icon (.ico for Windows, .icns for macOS; Linux uses the in-app window icon)
    icon_file = None
    if sys.platform == 'win32':
        icon_file = os.path.join("assets", "icon.ico")
    elif sys.platform == 'darwin':
        icon_file = os.path.join("assets", "icon.icns")
    if icon_file and os.path.isfile(icon_file):
        cmd.append(f"--icon={icon_file}")

    # Bundle assets (logo + icon used at runtime)
    if os.path.isdir("assets"):
        cmd.append(f"--add-data=assets{os.pathsep}assets")

    # Include local bin/ folder if it exists (for bundled ffmpeg/ffprobe)
    if os.path.isdir("bin"):
        cmd.append(f"--add-data=bin{os.pathsep}bin")

    print("[*] Running command:", " ".join(cmd))
    subprocess.check_call(cmd)

    print("\n" + "=" * 60)
    print(f"[✓] BUILD COMPLETE!")
    print(f"Executable output is located in: dist/{APP_NAME}/")
    if sys.platform == 'win32':
        print(f"Launch via: dist\\{APP_NAME}\\{APP_NAME}.exe")
        print(f"\n[Tip] You can place 'ffmpeg.exe' directly inside dist\\{APP_NAME}\\ alongside AudioJoinerStudio.exe")
    elif sys.platform == 'darwin':
        print(f"Launch via: dist/{APP_NAME}.app")
    else:
        print(f"Launch via: dist/{APP_NAME}/{APP_NAME}")
    print("=" * 60)

if __name__ == "__main__":
    build()
