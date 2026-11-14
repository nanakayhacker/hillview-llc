@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title AMOP - Alluvial Mining Operations Platform - Setup and Launch

echo ============================================================
echo  AMOP - Alluvial Mining Operations Platform
echo  One-click install, verify and launch
echo ============================================================
echo.

rem --- 1. Find a usable Python (3.10+) --------------------------------------
set "PYLAUNCHER="
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 --version >nul 2>nul
    if %ERRORLEVEL% EQU 0 set "PYLAUNCHER=py -3"
)
if not defined PYLAUNCHER (
    where python >nul 2>nul
    if %ERRORLEVEL% EQU 0 set "PYLAUNCHER=python"
)
if not defined PYLAUNCHER (
    echo [ERROR] Python was not found on this computer.
    echo.
    echo   1. Download Python 3.11 or later from https://www.python.org/downloads/
    echo   2. During install, TICK "Add python.exe to PATH"
    echo   3. Re-run this build_windows.bat afterwards
    echo.
    pause
    exit /b 1
)
echo [OK] Using: %PYLAUNCHER%
%PYLAUNCHER% --version

rem --- 2. Create / reuse a virtual environment -------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [1/5] Creating virtual environment in .venv ...
    %PYLAUNCHER% -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Could not create the virtual environment. See the message above.
        pause
        exit /b 1
    )
) else (
    echo.
    echo [1/5] Virtual environment already exists - reusing .venv
)

set "VENV_PY=.venv\Scripts\python.exe"

rem --- 3. Install dependencies -----------------------------------------------
echo.
echo [2/5] Installing dependencies (this can take a few minutes the first time) ...
"%VENV_PY%" -m pip install --upgrade pip --quiet
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Could not upgrade pip. Check your internet connection and try again.
    pause
    exit /b 1
)
"%VENV_PY%" -m pip install -r requirements.txt --quiet
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Dependency installation failed. See the message above.
    pause
    exit /b 1
)
"%VENV_PY%" -m pip install -e . --quiet
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Could not install the alluvial_mcp package. See the message above.
    pause
    exit /b 1
)
echo [OK] Dependencies installed.

rem --- 4. Run the golden test suite -------------------------------------------
echo.
echo [3/5] Verifying the platform against the golden test fixtures ...
"%VENV_PY%" -m pytest tests\ -q
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] One or more golden tests failed. The platform may not be computing
    echo         correctly on this machine. Please report this output.
    pause
    exit /b 1
)
echo [OK] All golden tests passed.

rem --- 5. Generate the BI exports (CSV + Tableau .twb + Power BI .pbids) ------
echo.
echo [4/5] Generating BI exports (CSV extracts, Tableau .twb, Power BI .pbids) ...
"%VENV_PY%" scripts\generate_bi_exports.py
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] BI export generation failed - continuing anyway. The built-in
    echo           dashboard inside the app does not need these files.
)

rem --- 6. Launch the application ------------------------------------------------
echo.
echo [5/5] Launching AMOP. Your browser should open automatically.
echo        If it does not, open the "Local URL" shown below.
echo.
echo        Close this window (or press Ctrl+C) to stop the platform.
echo ============================================================
echo.
"%VENV_PY%" -m streamlit run streamlit_app\streamlit_app.py

echo.
echo AMOP has stopped.
pause
