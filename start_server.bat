@echo off
echo Starting Misumi XY Stage Web Controller...
echo.
echo The web interface will be available at:
echo http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.

cd /d "%~dp0"
call venv\Scripts\activate.bat
uvicorn app:app --reload --host 0.0.0.0 --port 8000
