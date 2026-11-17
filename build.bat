@echo off
setlocal

echo ========================================
echo        Auto Typer - Build Script
echo ========================================
echo.

set VERSION=%1
if "%VERSION%"=="" set VERSION=0.0.0
echo Building version %VERSION%
echo.

echo Checking for PyInstaller...
python -m PyInstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing now...
    pip install pyinstaller
    echo.
)

echo Building the application folder...
echo.

pyinstaller --onedir --windowed --noconsole ^
--icon=icon.ico ^
--add-data "icon.ico;." ^
--hidden-import=PyQt5.sip ^
--hidden-import=pyautogui ^
--clean --noconfirm ^
--name="Auto Typer" ^
Typer.py

if %errorlevel% neq 0 (
    echo.
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo Building the installer...
echo.

set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
    echo Inno Setup 6 was not found, so the installer was skipped.
    echo Install it from https://jrsoftware.org/isdl.php and run this script again.
    echo The application folder is ready in "dist\Auto Typer".
    pause
    exit /b 0
)

%ISCC% /DMyAppVersion=%VERSION% installer.iss
if %errorlevel% neq 0 (
    echo.
    echo Installer build failed.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build Finished!
echo.
echo Installer: installer_output\Auto-Typer-Setup-v%VERSION%.exe
echo App folder: dist\Auto Typer
echo.
pause
