@echo off
setlocal

REM Проверяем наличие build_portable.py в текущей директории
if exist "build_portable.py" (
    set "BUILDER_PATH=build_portable.py"
) else if exist "..\build_portable.py" (
    set "BUILDER_PATH=..\build_portable.py"
) else (
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
python "%BUILDER_PATH%"
pause