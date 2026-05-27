@echo off
cd /d "%~dp0"
where pythonw >/dev/null 2>&1 && (
    start pythonw download_gui.py
) || where python >/dev/null 2>&1 && (
    start pythonw download_gui.py
) || (
    echo Python이 설치되어 있지 않습니다.
    echo https://www.python.org 에서 설치 후 다시 실행해주세요.
    pause
)
