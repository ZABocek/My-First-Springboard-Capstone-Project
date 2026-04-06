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
:: Step 2b: Check for email (SMTP) configuration
::
:: Registration emails are sent via an SMTP server.  Without a .env
:: file that points to a real mail server, emails will never arrive.
:: ────────────────────────────────────────────────────────────────────
echo.
if not exist "%~dp0.env" (
    echo [WARNING] No .env file found.
    echo           Registration emails will NOT be delivered until you
    echo           create a .env file with your Gmail SMTP settings.
    echo           Copy .env.example to .env and follow the instructions
    echo           inside it.
    echo.
) else (
    findstr /i "^MAIL_SERVER=localhost" "%~dp0.env" >nul 2>&1
    if !errorlevel! == 0 (
        echo [WARNING] .env has MAIL_SERVER=localhost, which cannot
        echo           deliver real email.  Update it with your Gmail
        echo           SMTP settings.  See .env.example for instructions.
        echo.
    ) else (
        echo [OK] Email configuration found in .env.
    )
)

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
:: Step 3b: Start the Celery email-delivery worker in a separate window
::
:: The Celery worker picks up email tasks queued by Flask and delivers
:: them via the SMTP server configured in .env.  Without this worker
:: running, verification emails are queued but never sent.
::
:: --pool=solo is required on Windows; the default 'prefork' pool uses
:: multiprocessing which is unreliable on Windows.
:: ────────────────────────────────────────────────────────────────────
echo.
echo [INFO] Stopping any existing Celery workers before starting a fresh one...
%PYTHON_CMD% -m celery -A celery_worker control shutdown >nul 2>&1
timeout /t 2 >nul 2>&1

echo [INFO] Starting email-delivery worker in a separate window...
start "Cocktail Chronicles Email Worker" /d "%~dp0." cmd /k %PYTHON_CMD% -m celery -A celery_worker worker --loglevel=warning --pool=solo
echo [OK] Email worker window opened  ^(keep it open to receive emails^).

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
echo   Email   :  Handled by the Email Worker window.
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

