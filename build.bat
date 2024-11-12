@echo off
echo Building web interface...
cd /d "%~dp0web"

if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo Error installing dependencies
        pause
        exit /b 1
    )
)

echo Running build...
call npm run build
if errorlevel 1 (
    echo Error during build
    pause
    exit /b 1
)

echo Build completed successfully!
timeout /t 3