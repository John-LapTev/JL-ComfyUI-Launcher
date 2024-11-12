@echo off
setlocal

REM Переходим в директорию, где находится bat-файл
cd /d "%~dp0"

echo Current directory: %CD%

REM Проверяем наличие build_portable.py в текущей директории
if exist "build_portable.py" (
    echo Found in current directory
    set "BUILDER_PATH=build_portable.py"
) else if exist "..\build_portable.py" (
    echo Found in parent directory
    set "BUILDER_PATH=..\build_portable.py"
) else (
    echo Checking current directory: %CD%\build_portable.py
    echo Checking parent directory: %CD%\..\build_portable.py
    echo Error: build_portable.py not found!
    echo Please make sure you're in the correct directory
    pause
    exit /b 1
)

REM Проверяем права администратора
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrative privileges...
    powershell Start-Process -FilePath "%~f0" -ArgumentList "am_admin" -Verb RunAs
    exit /b
)

REM Запускаем build_portable.py
echo Running: python "%BUILDER_PATH%"
python "%BUILDER_PATH%"
pause