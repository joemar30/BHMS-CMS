@echo off
echo ========================================================
echo Starting Boarding House Management System...
echo ========================================================

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found in "venv" folder.
    echo Please ensure the venv exists in this directory.
    pause
    exit /b
)

REM Activate the virtual environment
call venv\Scripts\activate

REM Run the Django server automatically
echo Server is starting... Open http://127.0.0.1:8000 in your browser!
python manage.py runserver

pause
