@echo off
setlocal enabledelayedexpansion

title Cocktail Chronicles - Starting...

echo.
echo ============================================================
echo   Cocktail Chronicles - App Launcher
echo ============================================================
echo.

:: ── Step 1: Locate Python ────────────────────────────────────
set PYTHON_CMD=

:: Prefer the project .venv if present
if exist "%~dp0.venv\Scripts\python.exe" (
    set PYTHON_CMD="%~dp0.venv\Scripts\python.exe"
    echo [OK] Found virtual environment: .venv
    goto :deps
)

:: Fall back to venv
if exist "%~dp0venv\Scripts\python.exe" (
    set PYTHON_CMD="%~dp0venv\Scripts\python.exe"
    echo [OK] Found virtual environment: venv
    goto :deps
)

:: Fall back to system Python
where python >nul 2>&1
if !errorlevel! == 0 (
    set PYTHON_CMD=python
    echo [INFO] No virtual environment found - using system Python.
    echo        Tip: create one with:  python -m venv .venv
    goto :deps
)

echo [ERROR] Python was not found. Please install Python 3.9+ and try again.
echo         Download from: https://www.python.org/downloads/
pause
exit /b 1

:: ── Step 2: Install / verify dependencies ────────────────────
:deps
echo.
echo [INFO] Checking dependencies...
%PYTHON_CMD% -m pip install -r "%~dp0requirements.txt" --quiet
if !errorlevel! neq 0 (
    echo [ERROR] Failed to install dependencies. Check your internet connection
    echo         or run:  pip install -r requirements.txt
    pause
    exit /b 1
)
echo [OK] Dependencies satisfied.

:: ── Step 3: Apply any pending database migrations ──────────
echo.
echo [INFO] Applying database migrations (flask db upgrade)...
set FLASK_APP=app.py
%PYTHON_CMD% -m flask db upgrade
if !errorlevel! neq 0 (
    echo [WARNING] Migration step reported an error. The server will still start,
    echo          but the database schema may be outdated.
)
echo [OK] Database schema is up to date.

:: ── Step 4: Open browser after a short delay ─────────────────
echo.
echo [INFO] Opening browser at http://127.0.0.1:5000 ...
start "" /b cmd /c "timeout /t 3 >nul && start http://127.0.0.1:5000"

:: ── Step 5: Start the Flask app ──────────────────────────────
echo.
echo ============================================================
echo   Server starting at http://127.0.0.1:5000
echo   Press CTRL+C in this window to stop the server.
echo ============================================================
echo.

%PYTHON_CMD% "%~dp0run_app.py"

echo.
echo [INFO] Server stopped.
pause
endlocal
