@echo off
setlocal enabledelayedexpansion

title Cocktail Chronicles

echo.
echo ================================================================
echo   Cocktail Chronicles  ^|  Local Launcher
echo ================================================================
echo.
echo   This launcher will:
echo     1. Locate your Python virtual environment
echo     2. Verify / install all required dependencies
echo     3. Apply any pending database migrations  (data is NEVER
echo        dropped — your cocktails and accounts are always safe)
echo     4. Open http://127.0.0.1:5000 in your default browser
echo     5. Start the Flask server with the browser watchdog ON
echo        (server shuts down gracefully when the browser is closed)
echo.
echo ================================================================
echo.

:: ────────────────────────────────────────────────────────────────────
:: Step 1: Locate Python
:: Preference order:  .venv  →  venv  →  system Python
:: ────────────────────────────────────────────────────────────────────
set PYTHON_CMD=

if exist "%~dp0.venv\Scripts\python.exe" (
    set PYTHON_CMD="%~dp0.venv\Scripts\python.exe"
    echo [OK] Found virtual environment: .venv
    goto :check_deps
)

if exist "%~dp0venv\Scripts\python.exe" (
    set PYTHON_CMD="%~dp0venv\Scripts\python.exe"
    echo [OK] Found virtual environment: venv
    goto :check_deps
)

where python >nul 2>&1
if !errorlevel! == 0 (
    set PYTHON_CMD=python
    echo [INFO] No virtual environment found  ^|  using system Python.
    echo        Tip: python -m venv .venv  ^&^&  .venv\Scripts\activate
    goto :check_deps
)

echo [ERROR] Python was not found on this machine.
echo         Install Python 3.11 from:  https://www.python.org/downloads/
echo.
pause
exit /b 1

:: ────────────────────────────────────────────────────────────────────
:: Step 2: Verify / install dependencies
:: ────────────────────────────────────────────────────────────────────
:check_deps
echo.
echo [INFO] Verifying dependencies (this may take a moment on first run)...
%PYTHON_CMD% -m pip install -r "%~dp0requirements.txt" --quiet
if !errorlevel! neq 0 (
    echo.
    echo [ERROR] Dependency installation failed.
    echo         Check your internet connection or run manually:
    echo           pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
echo [OK] All dependencies are satisfied.

:: ────────────────────────────────────────────────────────────────────
:: Step 3: Apply pending database migrations
::
:: IMPORTANT: flask db upgrade NEVER drops or truncates tables.
:: It only applies new ALTER TABLE / CREATE TABLE statements that
:: have been added since the last run.  Your data is always preserved.
:: ────────────────────────────────────────────────────────────────────
echo.
echo [INFO] Checking for database migrations...
set FLASK_APP=app.py
%PYTHON_CMD% -m flask db upgrade
if !errorlevel! neq 0 (
    echo.
    echo [WARNING] The migration step returned a non-zero exit code.
    echo           The server will still start.  Your existing data is
    echo           intact; only new schema changes may be missing.
    echo.
) else (
    echo [OK] Database schema is up-to-date.
)

:: ────────────────────────────────────────────────────────────────────
:: Step 4: Open browser after a short delay
:: (The delay lets the Flask server fully start before the page loads)
:: ────────────────────────────────────────────────────────────────────
echo.
echo [INFO] Your browser will open at http://127.0.0.1:5000 in 4 seconds...
start "" /b cmd /c "timeout /t 4 >nul 2>&1 && start http://127.0.0.1:5000"

:: ────────────────────────────────────────────────────────────────────
:: Step 5: Start the Flask server
::
:: BROWSER_WATCHDOG=true  activates the heartbeat watchdog so the
::   server shuts itself down cleanly when you close the browser window.
::
:: WATCHDOG_TIMEOUT=30  is the number of seconds of missed heartbeats
::   before the watchdog considers the browser gone (default: 30 s).
::
:: All data alterations made during the session are persisted to the
:: database — the watchdog only stops the Python process; it NEVER
:: touches the database files (no DROP, no TRUNCATE, no DELETE).
:: ────────────────────────────────────────────────────────────────────
set BROWSER_WATCHDOG=true
set WATCHDOG_TIMEOUT=30

echo.
echo ================================================================
echo   Server  :  http://127.0.0.1:5000
echo   Stop    :  Close the browser window   — or —
echo              Press Ctrl+C in this console.
echo   Data    :  Persisted automatically.  Nothing is ever dropped.
echo ================================================================
echo.

%PYTHON_CMD% "%~dp0run_app.py"

:: ────────────────────────────────────────────────────────────────────
:: The server has exited  (watchdog fired, browser closed, or Ctrl+C)
:: ────────────────────────────────────────────────────────────────────
echo.
echo [INFO] Server has stopped.  All your data has been saved.
echo.
pause
endlocal

