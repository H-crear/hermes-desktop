@echo off
cd /d C:\hermes-desktop
echo Starting Hermes Desktop Control Server...
if "%HERMES_DESKTOP_KEY%"=="" (
    echo WARNING: HERMES_DESKTOP_KEY environment variable is not set.
    echo A random API key will be auto-generated. See console output for the key.
    echo To set a permanent key: setx HERMES_DESKTOP_KEY "your-secret-key"
    echo.
)
start "" python windows_desktop_server.py
echo Server started.
