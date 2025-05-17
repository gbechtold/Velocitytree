@echo off
REM Velocitytree Setup Script for Windows
REM Automatically creates virtual environment and installs dependencies

echo Velocitytree Setup Script
echo ==========================

REM Check if Python 3 is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python 3 is not installed. Please install Python 3.8 or higher.
    exit /b 1
)

echo Python detected

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment already exists
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install Velocitytree in development mode
echo Installing Velocitytree...
pip install -e .

REM Install development dependencies if requested
if "%1"=="--dev" (
    echo Installing development dependencies...
    pip install -r requirements-dev.txt
)

echo.
echo Setup complete!
echo.
echo To activate the virtual environment, run:
echo   venv\Scripts\activate
echo.
echo To get started with Velocitytree, run:
echo   vtree --help
echo.