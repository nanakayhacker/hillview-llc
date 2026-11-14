@echo off
rem Opens AMOP after it has been installed once with build_windows.bat.
cd /d "%~dp0"
title AMOP - Alluvial Mining Operations Platform

if not exist ".venv\Scripts\python.exe" (
    echo AMOP is not installed yet in this folder.
    echo Double-click build_windows.bat first; it installs everything and opens the platform.
    echo.
    pause
    exit /b 1
)

echo Opening AMOP. Your browser should open at http://localhost:8501
echo If it does not, type that address into your browser.
echo.
echo Keep this window open while you work. Close it (or press Ctrl+C) to stop AMOP.
echo.
".venv\Scripts\python.exe" -m streamlit run streamlit_app\streamlit_app.py

echo.
echo AMOP has stopped.
pause
