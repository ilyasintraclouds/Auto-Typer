@echo off
echo ========================================
echo        Auto Typer - Build Script
echo ========================================
echo.

echo Checking for PyInstaller...
python -c "import pyinstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing now...
    pip install pyinstaller
    echo.
)

echo Starting build process...
echo.

pyinstaller --onefile --windowed --noconsole ^
--icon=icon.ico ^
--add-data "icon.ico;." ^
--hidden-import=PyQt5.sip ^
--hidden-import=pyautogui ^
--clean ^
--name="Auto Typer" ^
Typer.py

echo.
echo ========================================
echo Build Finished!
echo.
echo Executable should be in the "dist" folder.
echo File name: Auto Typer.exe
echo.
pause