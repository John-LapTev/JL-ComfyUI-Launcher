@echo off
chcp 65001 > nul

:: Запрос прав администратора
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Запрашиваем права администратора...
    powershell Start-Process -FilePath "%~f0" -ArgumentList "am_admin" -Verb RunAs
    exit /b
)

:: Если скрипт запущен с правами администратора
if "%1"=="am_admin" (
    cd /d "%~dp0"
) else (
    exit /b
)

echo Начинаем установку недостающих пакетов...
echo.

:: Переходим в директорию venv\Scripts и активируем виртуальное окружение
cd launcher\venv\Scripts
echo Активация виртуального окружения...
call activate.bat

:: Переходим в директорию server
cd ..\..\server

:: Устанавливаем пакеты
echo.
echo Установка amqp...
pip install amqp
echo.
echo Установка celery...
pip install celery
echo.
echo Установка requests...
pip install requests
echo.
echo Установка tqdm...
pip install tqdm
echo.
echo Установка redis...
pip install redis

:: Деактивируем виртуальное окружение
echo.
echo Деактивация виртуального окружения...
call deactivate

echo.
echo Установка завершена.
echo.
echo Теперь вы можете закрыть это окно и запустить start.bat
echo от имени администратора.
echo.
pause