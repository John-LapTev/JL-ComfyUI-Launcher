import os
import requests
import zipfile
import subprocess
import shutil
import sys
import stat
from tqdm import tqdm
import json
import tempfile
import time
import logging
import pkg_resources
import platform
import torch
from pkg_resources import DistributionNotFound, VersionConflict
from typing import List, Optional, Dict

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы для типов сборок
BUILD_TYPE_CUDA = "cuda"
BUILD_TYPE_DIRECTML = "directml"
BUILD_TYPE_MACOS = "macos"

def select_build_type():
    """Выбор типа сборки"""
    print("\nSelect build type:")
    print("1. Windows NVIDIA (CUDA)")
    print("2. Windows AMD/Intel (DirectML)")
    print("3. MacOS")
    
    while True:
        choice = input("\nEnter your choice (1-3): ").strip()
        if choice == "1":
            return BUILD_TYPE_CUDA
        elif choice == "2":
            return BUILD_TYPE_DIRECTML
        elif choice == "3":
            return BUILD_TYPE_MACOS
        else:
            print("Invalid choice. Please enter 1, 2 or 3.")

def install_pytorch_for_build_type(pip_path, build_type):
    """Установка PyTorch в зависимости от типа сборки"""
    try:
        if build_type == BUILD_TYPE_CUDA:
            logger.info("Installing PyTorch with CUDA support...")
            subprocess.run([
                pip_path,
                'install',
                'torch==2.2.1+cu121',
                'torchvision==0.17.1+cu121',
                'torchaudio==2.2.1+cu121',
                '--index-url', 'https://download.pytorch.org/whl/cu121'
            ], check=True)
        elif build_type == BUILD_TYPE_DIRECTML:
            logger.info("Installing PyTorch with DirectML support...")
            subprocess.run([
                pip_path,
                'install',
                'torch==2.2.1',
                'torchvision==0.17.1',
                'torchaudio==2.2.1',
            ], check=True)
            subprocess.run([
                pip_path,
                'install',
                'torch-directml'
            ], check=True)
        elif build_type == BUILD_TYPE_MACOS:
            logger.info("Installing PyTorch for MacOS...")
            subprocess.run([
                pip_path,
                'install',
                'torch',
                'torchvision',
                'torchaudio'
            ], check=True)
    except Exception as e:
        logger.error(f"Failed to install PyTorch: {e}")
        raise

def create_start_script(base_dir, build_type):
    """Создание стартового скрипта в зависимости от типа сборки"""
    if build_type == BUILD_TYPE_MACOS:
        start_script_content = '''#!/bin/bash
# Set environment variables
export PATH="$PWD/python/bin:$PWD/redis:$PWD/nodejs:$PATH"
export PYTHONHOME="$PWD/python"
export PYTHONPATH="$PWD/launcher"

# Start Redis Server
echo "Starting Redis Server..."
./redis/redis-server ./redis/redis.conf &
sleep 5

# Activate virtual environment and start server
echo "Starting ComfyUI Launcher..."
cd launcher
source venv/bin/activate
cd server

# Start Celery Worker
echo "Starting Celery Worker..."
python -m celery -A celery_app worker --pool=solo -l info --purge &

# Open browser
open http://localhost:4000

# Start server
python server.py
'''
        script_path = os.path.join(base_dir, 'start.sh')
        with open(script_path, 'w', newline='\n') as f:
            f.write(start_script_content)
        os.chmod(script_path, 0o755)
    
    else:
        start_bat_content = '''@echo off
:: Request admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrative privileges...
    powershell -Command "Start-Process -Verb RunAs -FilePath '%~f0' -ArgumentList 'am_admin'"
    exit /b
)

:: If script is run with am_admin argument, we have admin rights
if "%1"=="am_admin" (
    cd /d "%~dp0"
) else (
    exit /b
)

setlocal

:: Set UTF-8 encoding
chcp 65001 > nul

:: Check and create .celery folder if it doesn't exist
if not exist "%~dp0launcher\\server\\.celery" mkdir "%~dp0launcher\\server\\.celery"
'''
        
        if build_type == BUILD_TYPE_CUDA:
            start_bat_content += '''
:: Set CUDA environment
set "PATH=%~dp0cuda;%~dp0python\\Scripts;%~dp0python;%~dp0redis;%~dp0nodejs;%PATH%"
set "CUDA_PATH=%~dp0cuda"
'''
        elif build_type == BUILD_TYPE_DIRECTML:
            start_bat_content += '''
:: Set DirectML environment
set "PATH=%~dp0python\\Scripts;%~dp0python;%~dp0redis;%~dp0nodejs;%PATH%"
set "DIRECTML_DEVICE=0"
'''

        start_bat_content += '''
:: Set Python environment
set "PYTHONHOME=%~dp0python"
set "PYTHONPATH=%~dp0launcher"

:: Fix paths
set "PATH=%PATH:"=%"
set "PYTHONHOME=%PYTHONHOME:"=%"
set "PYTHONPATH=%PYTHONPATH:"=%"

echo Starting Redis Server...
start "" "%~dp0redis\\redis-server.exe" "%~dp0redis\\redis.windows.conf"
timeout /t 5 > nul

echo Starting ComfyUI Launcher...
cd /d "%~dp0launcher"
call venv\\Scripts\\activate.bat
cd server

echo Starting Celery Worker...
start cmd /k "cd /d %~dp0launcher\\server && set PYTHONPATH=%~dp0launcher && %~dp0python\\python.exe -m celery -A celery_app worker --pool=solo -l info --purge"
timeout /t 2 > nul

title ComfyUI Launcher
echo Opening http://localhost:4000 in your default browser...
start http://localhost:4000

"%~dp0launcher\\venv\\Scripts\\python.exe" server.py
pause
'''
        script_path = os.path.join(base_dir, 'start.bat')
        with open(script_path, 'w') as f:
            f.write(start_bat_content)

# Функция проверки установки отдельного пакета
def verify_package_installation(pip_path: str, package: str) -> bool:
    """Проверка установки пакета через pip"""
    try:
        result = subprocess.run(
            [pip_path, 'show', package],
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError:
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке установки {package}: {e}")
        return False

# Функция проверки возможности импорта
def verify_dependencies():
    """Проверка возможности импорта всех необходимых зависимостей"""
    logger.info("Проверка возможности импорта зависимостей...")
    
    dependencies = [
        'numpy', 'opencv-python-headless', 'scikit-image', 'scikit-learn',
        'scipy', 'huggingface-hub', 'safetensors', 'transformers',
        'accelerate', 'matplotlib', 'protobuf', 'pydantic', 'einops',
        'requests', 'tqdm', 'amqp', 'celery', 'redis'
    ]
    
    missing = []
    import_errors = []
    
    for dep in dependencies:
        try:
            __import__(dep)
        except ImportError as e:
            missing.append(dep)
            import_errors.append(f"{dep}: {str(e)}")
    
    if missing:
        logger.warning("Отсутствующие или неработающие зависимости:")
        for error in import_errors:
            logger.warning(f"  - {error}")
        return False
    
    logger.info("Все зависимости успешно проверены!")
    return True

# Функция полной проверки зависимостей
def full_dependency_check(pip_path: str) -> bool:
    """Полная проверка зависимостей"""
    logger.info("Начинаем полную проверку зависимостей...")
    
    dependencies = [
        'numpy', 'opencv-python-headless', 'scikit-image', 'scikit-learn',
        'scipy', 'huggingface-hub', 'safetensors', 'transformers',
        'accelerate', 'matplotlib', 'protobuf', 'pydantic', 'einops',
        'requests', 'tqdm', 'amqp', 'celery', 'redis'
    ]
    
    missing_installations = []
    for dep in dependencies:
        if not verify_package_installation(pip_path, dep):
            missing_installations.append(dep)
    
    if missing_installations:
        logger.warning(f"Не установлены пакеты: {', '.join(missing_installations)}")
        return False
        
    if not verify_dependencies():
        logger.warning("Проверка импорта зависимостей не пройдена")
        return False
        
    logger.info("Полная проверка зависимостей успешно завершена!")
    return True

# Функция установки зависимостей
def install_dependencies(pip_path: str) -> bool:
    """Установка зависимостей с улучшенной обработкой ошибок"""
    try:
        logger.info("Установка базовых зависимостей...")
        
        # Сначала обновляем pip и устанавливаем критические пакеты
        critical_packages = [
            'pip',
            'setuptools',
            'wheel',
            'virtualenv'
        ]
        
        for package in critical_packages:
            try:
                logger.info(f"Установка критического пакета {package}...")
                subprocess.run([
                    pip_path,
                    'install',
                    '--upgrade',
                    '--no-cache-dir',
                    package
                ], check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Ошибка установки {package}: {e}")
                raise
        
        # Основные пакеты с фиксированными версиями
        base_packages = [
            'numpy==1.24.4',
            'requests==2.31.0',
            'tqdm>=4.65.0',
            'amqp==5.2.0',
            'pillow>=10.0.0',
            'pyyaml>=5.1',
            'redis==4.5.4',
            'kombu==5.3.2',
            'celery==5.3.4',
            'flask==2.3.3',
            'click==8.1.7',
            'billiard==4.2.0',
            'vine==5.1.0',
            'async-timeout==4.0.3',
            'GitPython==3.1.40',
            'psutil<6.0.0',
            'werkzeug>=3.0.0'
        ]
        
        # Зависимости для обработки изображений
        image_packages = [
            'opencv-python-headless>=4.9.0.80',
            'scikit-image>=0.21.0',
            'scikit-learn>=1.3.2',
            'scipy>=1.10.0',
            'matplotlib>=3.8.0'
        ]
        
        # AI компоненты
        ai_packages = [
            'huggingface-hub>=0.20.2',
            'safetensors>=0.3.1',
            'transformers>=4.36.0',
            'accelerate>=0.21.0',
            'diffusers==0.25.1',
            'einops>=0.7.0',
            'timm<=0.6.7'
        ]
        
        # Дополнительные библиотеки
        extra_packages = [
            'protobuf>=3.20.2',
            'pydantic>=2.7.0',
            'regex!=2019.12.17',
            'pre-commit'
        ]

        # Специальные пакеты
        special_packages = [
            'controlnet-aux==0.0.9',
            'insightface==0.7.3'
        ]
        
        # Установка всех пакетов по категориям
        all_packages = {
            "Базовые пакеты": base_packages,
            "Обработка изображений": image_packages,
            "AI компоненты": ai_packages,
            "Дополнительные библиотеки": extra_packages,
            "Специальные пакеты": special_packages
        }
        
        for category, packages in all_packages.items():
            logger.info(f"\nУстановка категории: {category}")
            for package in packages:
                try:
                    # Сначала пробуем установить сам пакет
                    logger.info(f"Установка {package}...")
                    subprocess.run([
                        pip_path,
                        'install',
                        '--no-cache-dir',
                        '--no-deps',
                        '--no-warn-script-location',
                        package
                    ], check=True)
                    
                    # Затем устанавливаем его зависимости
                    subprocess.run([
                        pip_path,
                        'install',
                        '--no-cache-dir',
                        '--no-warn-script-location',
                        package
                    ], check=True)
                    
                    # Проверяем установку
                    if not verify_package_installation(pip_path, package.split('==')[0].split('>=')[0]):
                        raise Exception(f"Пакет {package} не был корректно установлен")
                        
                except subprocess.CalledProcessError as e:
                    logger.error(f"Ошибка установки {package}: {e}")
                    if package in ['numpy', 'requests', 'tqdm', 'amqp', 'celery', 'redis']:
                        raise
                    continue
                except Exception as e:
                    logger.error(f"Непредвиденная ошибка при установке {package}: {e}")
                    if package in ['numpy', 'requests', 'tqdm', 'amqp', 'celery', 'redis']:
                        raise
                    continue
        
        return True
        
    except Exception as e:
        logger.error(f"Критическая ошибка при установке зависимостей: {e}")
        return False
        
def check_cuda_installation():
    """Проверка наличия CUDA"""
    logger.info("\nChecking CUDA installation...")
    
    cuda_paths = [
        r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12",
        r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8"
    ]
    
    for path in cuda_paths:
        if os.path.exists(path):
            logger.info(f"✓ Found CUDA in: {path}")
            bin_path = os.path.join(path, 'bin')
            if os.path.exists(bin_path):
                logger.info(f"✓ Found CUDA bin directory: {bin_path}")
                return True
    
    logger.warning("✗ CUDA installation not found in standard locations")
    return False

def download_file(url, filename, temp_dir=None):
    """Загрузка файла с индикатором прогресса"""
    target = os.path.join(temp_dir, filename) if temp_dir else filename
    if os.path.exists(target):
        logger.info(f"File {filename} already exists, skipping download...")
        return target
    
    logger.info(f"Downloading {filename}...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192
        
        with open(target, 'wb') as f:
            with tqdm(
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
                miniters=1,
                desc=filename,
                bar_format='{desc}: {percentage:3.0f}%|{bar:30}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]',
                dynamic_ncols=True,
                leave=False
            ) as pbar:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        size = len(chunk)
                        f.write(chunk)
                        pbar.update(size)
                        
        logger.info(f"Downloaded {filename}")
        return target
    except Exception as e:
        logger.error(f"Error downloading {filename}: {e}")
        if os.path.exists(target):
            os.remove(target)
        raise
        
def safe_remove(path):
    """Безопасное удаление файла или директории"""
    if not os.path.exists(path):
        return
        
    def on_rm_error(func, path, exc_info):
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception as e:
            logger.error(f"Error removing {path}: {e}")

    try:
        if os.path.isfile(path):
            os.chmod(path, stat.S_IWRITE)
            os.remove(path)
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for dir in dirs:
                    try:
                        os.chmod(os.path.join(root, dir), stat.S_IWRITE)
                    except:
                        pass
                for file in files:
                    try:
                        os.chmod(os.path.join(root, file), stat.S_IWRITE)
                    except:
                        pass
            shutil.rmtree(path, onerror=on_rm_error)
    except Exception as e:
        logger.warning(f"Warning: Could not remove {path}: {e}")

def copy_system_cuda_dlls(base_dir):
    """Копирование CUDA DLLs из системной установки"""
    logger.info("\nCopying system CUDA DLLs...")
    
    cuda_dir = os.path.join(base_dir, 'cuda')
    os.makedirs(cuda_dir, exist_ok=True)
    
    system_paths = [
        r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12\bin",
        r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin",
        r"C:\Program Files\NVIDIA\CUDNN\v8.9\bin",
        r"C:\Program Files\NVIDIA\CUDNN\v8.8\bin",
        r"C:\Program Files\NVIDIA Corporation\NVIDIA Broadcast\Assets\Plugins",
        r"C:\Windows\System32",
        r"C:\Windows\SysWOW64"
    ]
    
    copied_files = set()
    cuda_dll_found = False
    
    for system_path in system_paths:
        if os.path.exists(system_path):
            logger.info(f"Checking {system_path}")
            try:
                files = os.listdir(system_path)
                for file in files:
                    if file.lower().endswith('.dll') and ('cuda' in file.lower() or 'cudnn' in file.lower()):
                        src = os.path.join(system_path, file)
                        dst = os.path.join(cuda_dir, file)
                        try:
                            shutil.copy2(src, dst)
                            copied_files.add(file)
                            logger.info(f"✓ Copied {file}")
                            cuda_dll_found = True
                        except Exception as e:
                            logger.error(f"Error copying {file}: {e}")
            except Exception as e:
                logger.error(f"Error accessing {system_path}: {e}")
    
    if not cuda_dll_found:
        logger.warning("Warning: No CUDA DLL files found in system")
        return False
        
    logger.info(f"\nCopied {len(copied_files)} CUDA DLL files:")
    for file in sorted(copied_files):
        logger.info(f"  - {file}")
    
    return True

def create_models_config(base_dir):
    """Создание конфигурационного файла для моделей"""
    config = {
        "base_path": "./models",
        "checkpoints": "./models/checkpoints",
        "configs": "./models/configs",
        "loras": "./models/loras",
        "vae": "./models/vae",
        "controlnet": "./models/controlnet",
        "embeddings": "./models/embeddings",
        "upscale_models": "./models/upscale_models"
    }
    
    config_path = os.path.join(base_dir, 'launcher', 'models_config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    logger.info(f"Created models config at {config_path}")

def check_installation(base_dir):
    """Проверка корректности установки"""
    if platform.system() == "Darwin":  # MacOS
        required_files = [
            'python/bin/python',
            'redis/redis-server',
            'redis/redis.conf',
            'nodejs/bin/node',
            'launcher/venv/bin/python',
            'launcher/venv/bin/pip',
            'launcher/server/server.py',
            'launcher/models_config.json',
            'start.sh'
        ]
    else:  # Windows
        required_files = [
            'python/python.exe',
            'redis/redis-server.exe',
            'redis/redis.windows.conf',
            'nodejs/node.exe',
            'launcher/venv/Scripts/python.exe',
            'launcher/venv/Scripts/pip.exe',
            'launcher/server/server.py',
            'launcher/models_config.json',
            'start.bat'
        ]
    
    # Проверка CUDA DLLs только для Windows CUDA сборки
    if platform.system() == "Windows" and os.path.exists(os.path.join(base_dir, 'cuda')):
        cuda_path = os.path.join(base_dir, 'cuda')
        cuda_files = [f for f in os.listdir(cuda_path) if f.lower().endswith('.dll')]
        if cuda_files:
            logger.info(f"\n✓ Found {len(cuda_files)} CUDA DLLs")
        else:
            logger.warning("\n✗ No CUDA DLLs found")
    
    # Проверка Redis
    logger.info("\nChecking Redis...")
    if platform.system() == "Darwin":
        redis_path = os.path.join(base_dir, 'redis', 'redis-server')
        redis_conf_path = os.path.join(base_dir, 'redis', 'redis.conf')
    else:
        redis_path = os.path.join(base_dir, 'redis', 'redis-server.exe')
        redis_conf_path = os.path.join(base_dir, 'redis', 'redis.windows.conf')
        
    if os.path.exists(redis_path) and os.path.exists(redis_conf_path):
        logger.info("✓ Redis files found")
    else:
        logger.warning("✗ Redis files missing")
    
    missing_files = []
    for file in required_files:
        full_path = os.path.join(base_dir, file)
        if not os.path.exists(full_path):
            missing_files.append(file)
            logger.warning(f"✗ Missing: {file}")
        else:
            logger.info(f"✓ Found: {file}")
    
    return missing_files

# Функция создания виртуального окружения
def create_virtualenv(venv_path):
    """Создание виртуального окружения с улучшенной обработкой ошибок"""
    try:
        logger.info(f"Создание виртуального окружения: {venv_path}")
        
        # Преобразуем путь в абсолютный
        venv_path = os.path.abspath(venv_path)
        
        if os.path.exists(venv_path):
            logger.info(f"Виртуальное окружение уже существует: {venv_path}")
            return

        # Устанавливаем virtualenv
        logger.info("Установка virtualenv...")
        subprocess.run([
            "pip", "install", "--upgrade", "virtualenv"
        ], check=True)

        # Создаем виртуальное окружение
        logger.info("Создание виртуального окружения...")
        subprocess.run([
            "virtualenv", venv_path
        ], check=True)

        # Определяем пути к python и pip
        if os.name == "nt":  # Windows
            python_path = os.path.join(venv_path, 'Scripts', 'python.exe')
            pip_path = os.path.join(venv_path, 'Scripts', 'pip.exe')
        else:  # Linux/Mac
            python_path = os.path.join(venv_path, 'bin', 'python')
            pip_path = os.path.join(venv_path, 'bin', 'pip')

        # Обновляем pip
        logger.info("Обновление pip...")
        try:
            subprocess.run([
                python_path, '-m', 'pip', 'install', '--upgrade', 'pip'
            ], check=True)
        except subprocess.CalledProcessError as e:
            logger.warning(f"Не удалось обновить pip: {e}")

        # Устанавливаем зависимости
        if not install_dependencies(pip_path):
            raise Exception("Не удалось установить зависимости")

        # Выполняем полную проверку
        if not full_dependency_check(pip_path):
            raise Exception("Проверка зависимостей не пройдена")
            
        logger.info("Виртуальное окружение успешно создано и проверено")
        
    except Exception as e:
        logger.error(f"Ошибка создания виртуального окружения: {e}")
        if os.path.exists(venv_path):
            shutil.rmtree(venv_path, ignore_errors=True)
        raise

def build_portable(build_type):
    """Создание портативной версии"""
    base_dir = f'ComfyUI-Launcher-Portable-{build_type.upper()}'
    original_dir = os.getcwd()
    
    try:
        # Проверяем наличие CUDA только для CUDA сборки
        if build_type == BUILD_TYPE_CUDA:
            if not check_cuda_installation():
                logger.warning("\nWarning: CUDA installation not found!")
                response = input("Continue without CUDA support? (y/n): ")
                if not response.lower().startswith('y'):
                    return False
                logger.info("Continuing without CUDA support...")
            else:
                logger.info("CUDA installation found, will include GPU support.")

        # Создаем временную директорию для загрузок
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"\nUsing temporary directory: {temp_dir}")
            
            # Создаем структуру папок
            logger.info("\nCreating directory structure...")
            directories = ['python', 'redis', 'nodejs', 'launcher', 'models']
            if build_type == BUILD_TYPE_CUDA:
                directories.append('cuda')
            
            for dir_name in directories:
                os.makedirs(os.path.join(base_dir, dir_name), exist_ok=True)

            # Создаем структуру папок для моделей
            model_subdirs = ['checkpoints', 'configs', 'controlnet', 'embeddings', 
                           'loras', 'upscale_models', 'vae']
            for subdir in model_subdirs:
                os.makedirs(os.path.join(base_dir, 'models', subdir), exist_ok=True)

            # Создаем конфигурацию Redis
            logger.info("\nCreating Redis configuration...")
            if build_type == BUILD_TYPE_MACOS:
                redis_config_content = '''# Redis configuration file
port 6379
bind 127.0.0.1
maxmemory 100mb
maxmemory-policy allkeys-lru
'''
                with open(os.path.join(base_dir, 'redis', 'redis.conf'), 'w') as f:
                    f.write(redis_config_content)
            else:
                redis_config_content = '''# Redis configuration file
port 6379
bind 127.0.0.1
maxmemory 100mb
maxmemory-policy allkeys-lru
'''
                with open(os.path.join(base_dir, 'redis', 'redis.windows.conf'), 'w') as f:
                    f.write(redis_config_content)

            # Загружаем необходимые файлы
            if build_type == BUILD_TYPE_MACOS:
                files_to_download = {
                    'python.zip': 'https://www.python.org/ftp/python/3.10.6/python-3.10.6-macos11.pkg',  # Используйте правильную ссылку для MacOS
                    'redis.zip': 'https://download.redis.io/releases/redis-stable.tar.gz',
                    'nodejs.zip': 'https://nodejs.org/download/release/v16.20.2/node-v16.20.2-darwin-x64.tar.gz'
                }
            else:
                files_to_download = {
                    'python.zip': 'https://www.python.org/ftp/python/3.10.6/python-3.10.6-embed-amd64.zip',
                    'redis.zip': 'https://github.com/microsoftarchive/redis/releases/download/win-3.0.504/Redis-x64-3.0.504.zip',
                    'nodejs.zip': 'https://nodejs.org/download/release/v16.20.2/node-v16.20.2-win-x64.zip'
                }

            # Загрузка файлов
            downloaded_files = {}
            for filename, url in files_to_download.items():
                try:
                    downloaded_files[filename] = download_file(url, filename, temp_dir)
                except Exception as e:
                    logger.error(f"Error downloading {filename}: {e}")
                    return False

            # Распаковка файлов
            logger.info("\nExtracting files...")
            for filename, filepath in downloaded_files.items():
                target_dir = os.path.join(base_dir, filename.split('.')[0])
                logger.info(f"Extracting {filename} to {target_dir}")
                try:
                    with zipfile.ZipFile(filepath, 'r') as zip_ref:
                        zip_ref.extractall(target_dir)
                    
                    # Специальная обработка для Node.js
                    if filename == 'nodejs.zip':
                        time.sleep(1)
                        nodejs_inner_dir = os.path.join(target_dir, f"node-v16.20.2-win-x64")
                        if os.path.exists(nodejs_inner_dir):
                            for item in os.listdir(nodejs_inner_dir):
                                src = os.path.join(nodejs_inner_dir, item)
                                dst = os.path.join(target_dir, item)
                                if os.path.exists(dst):
                                    safe_remove(dst)
                                if os.path.isdir(src):
                                    shutil.copytree(src, dst)
                                else:
                                    shutil.copy2(src, dst)
                            safe_remove(nodejs_inner_dir)
                except Exception as e:
                    logger.error(f"Error extracting {filename}: {e}")
                    return False

            # Установка базовых пакетов в основной Python
            logger.info("\nInstalling base packages in main Python...")
            python_path = os.path.join(base_dir, 'python', 'python.exe')
            pip_path = os.path.join(base_dir, 'python', 'Scripts', 'pip.exe')
            
            # Сначала скачиваем get-pip.py
            logger.info("Downloading get-pip.py...")
            pip_url = "https://bootstrap.pypa.io/get-pip.py"
            get_pip_path = os.path.join(temp_dir, "get-pip.py")
            download_file(pip_url, "get-pip.py", temp_dir)

            # Распаковываем python310.zip если он существует
            python_zip = os.path.join(base_dir, 'python', 'python310.zip')
            if os.path.exists(python_zip):
                logger.info("Extracting python310.zip...")
                with zipfile.ZipFile(python_zip, 'r') as zip_ref:
                    zip_ref.extractall(os.path.join(base_dir, 'python', 'Lib'))

            # Создаем python310._pth
            pth_content = '''python310.zip
.
Lib
import site'''
            with open(os.path.join(base_dir, 'python', 'python310._pth'), 'w') as f:
                f.write(pth_content)

            # Устанавливаем pip
            logger.info("Installing pip...")
            subprocess.run([python_path, get_pip_path, "--no-warn-script-location"], check=True)

            # Создаем папку Scripts если её нет
            os.makedirs(os.path.join(base_dir, 'python', 'Scripts'), exist_ok=True)

            # Устанавливаем необходимые пакеты в основной Python
            logger.info("Installing required packages in main Python...")
            if not install_dependencies(pip_path):
                logger.error("Failed to install required packages in main Python")
                return False

            # Копируем CUDA DLLs только для CUDA сборки
            if build_type == BUILD_TYPE_CUDA:
                cuda_status = copy_system_cuda_dlls(base_dir)
                if not cuda_status:
                    logger.warning("\nWarning: Failed to copy CUDA DLLs, GPU support might be limited")
                    if not input("Continue without CUDA support? (y/n): ").lower().startswith('y'):
                        return False

            # Клонируем ComfyUI Launcher
            logger.info("\nCloning ComfyUI Launcher...")
            launcher_dir = os.path.join(base_dir, 'launcher')
            retry_count = 3
            while retry_count > 0:
                try:
                    if os.path.exists(launcher_dir):
                        time.sleep(1)
                        safe_remove(launcher_dir)
                        time.sleep(1)
                    
                    subprocess.run(['git', 'clone', 'https://github.com/ComfyWorkflows/comfyui-launcher', 
                                launcher_dir], check=True)
                    break
                except Exception as e:
                    logger.error(f"Attempt {4-retry_count}/3: Error cloning repository: {e}")
                    retry_count -= 1
                    if retry_count == 0:
                        logger.error("Failed to clone repository after 3 attempts")
                        return False
                    time.sleep(2)

            # Копируем модифицированные файлы
            logger.info("\nCopying modified files...")
            modified_files = {
                'utils.py': '/server/utils.py',
                'settings.py': '/server/settings.py',
                'celery_app.py': '/server/celery_app.py',
                '__init__.py': '/server/__init__.py',
                'server.py': '/server/server.py',
                'tasks.py': '/server/tasks.py',
                'web/comfy_frame.html': '/web/comfy_frame.html',
                # Добавляем новые модифицированные файлы
                'web/src/components/SettingsUI.tsx': '/web/src/components/SettingsUI.tsx',
                'web/src/lib/types.ts': '/web/src/lib/types.ts',
                'web/src/pages/settings/page.tsx': '/web/src/pages/settings/page.tsx'
            }

            for file, dest_path in modified_files.items():
                src = os.path.join('modified_files', file)
                if os.path.exists(src):
                    dest = os.path.join(base_dir, 'launcher', dest_path.lstrip('/'))
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy2(src, dest)
                    logger.info(f"✓ Copied {file} to {dest}")
                else:
                    logger.warning(f"✗ Warning: {file} not found in modified_files directory")

            # Настройка виртуального окружения
            logger.info("\nSetting up virtual environment...")
            venv_path = os.path.join(base_dir, 'launcher', 'venv')
            try:
                # Создание виртуального окружения
                subprocess.run(['python', '-m', 'venv', venv_path], check=True)

                # Обновление pip
                logger.info("\nUpdating pip...")
                subprocess.run([
                    os.path.join(venv_path, 'Scripts', 'python.exe'),
                    '-m', 'pip', 'install', '--upgrade', 'pip'
                ], check=True)

                # Установка зависимостей в виртуальное окружение
                logger.info("Installing dependencies in virtual environment...")
                venv_pip = os.path.join(venv_path, 'Scripts', 'pip.exe')
                if not install_dependencies(venv_pip):
                    raise Exception("Failed to install dependencies in virtual environment")

                # Проверяем установленные зависимости
                if not verify_dependencies():
                    logger.warning("Some dependencies may be missing in virtual environment")

                # Установка дополнительных зависимостей
                logger.info("\nInstalling additional dependencies...")
                subprocess.run([
                    venv_pip,
                    'install', '-r', os.path.join(base_dir, 'launcher', 'requirements.txt')
                ], check=True)

                # Установка PyTorch с CUDA/DirectML/Default
                logger.info("\nInstalling PyTorch...")
                install_pytorch_for_build_type(venv_pip, build_type)

            except Exception as e:
                logger.error(f"Error during Python environment setup: {e}")
                return False

            # Создаем конфигурацию моделей
            create_models_config(base_dir)

            # Создаем стартовый скрипт в зависимости от типа сборки
            create_start_script(base_dir, build_type)

            # Создаем readme.txt
            readme_content = f'''ComfyUI Launcher Portable ({build_type.upper()})
======================

Эта портативная версия включает все необходимые компоненты:
- Python 3.10.6
- Redis Server
- Node.js
'''
            if build_type == BUILD_TYPE_CUDA:
                readme_content += "- CUDA Runtime DLLs (для поддержки NVIDIA GPU)\n"
            elif build_type == BUILD_TYPE_DIRECTML:
                readme_content += "- DirectML (для поддержки AMD/Intel GPU)\n"
            
            readme_content += '''
Для запуска:
'''
            if build_type == BUILD_TYPE_MACOS:
                readme_content += '''1. Запустите start.sh (возможно потребуется выполнить chmod +x start.sh)
2. Браузер откроется автоматически (http://localhost:4000)
3. Готово!
'''
            else:
                readme_content += '''1. Запустите start.bat от имени администратора (при первом запуске)
2. Браузер откроется автоматически (http://localhost:4000)
3. Готово!
'''

            readme_content += '''
Примечание: 
- При первом запуске установка может занять некоторое время
- Модели будут автоматически скачиваться в папку models при необходимости
- Все проекты сохраняются в папке launcher/server/projects

Системные требования:
'''
            if build_type == BUILD_TYPE_CUDA:
                readme_content += '''- Windows 10/11
- NVIDIA GPU
  * Для GPU нужны последние драйверы NVIDIA
'''
            elif build_type == BUILD_TYPE_DIRECTML:
                readme_content += '''- Windows 10/11
- AMD или Intel GPU
  * Для GPU нужны последние драйверы
'''
            else:
                readme_content += '''- MacOS 11 или новее
- Apple Silicon (M1/M2) или Intel CPU
'''

            readme_content += '''- Минимум 8GB RAM
- 20GB свободного места на диске

Важно:
- Не перемещайте файлы внутри папок
- Не изменяйте структуру папок
- При возникновении проблем убедитесь, что:
  * Антивирус не блокирует работу
  * Все процессы ComfyUI закрыты перед запуском
'''

            if build_type != BUILD_TYPE_MACOS:
                readme_content += "  * Запускаете от имени администратора при первом запуске\n"

            readme_content += '''
При проблемах:
1. Закройте все окна ComfyUI
2. Удалите папку .celery в папке server, если она есть
'''

            if build_type == BUILD_TYPE_MACOS:
                readme_content += "3. Запустите start.sh\n"
            else:
                readme_content += "3. Запустите start.bat от имени администратора\n"

            with open(os.path.join(base_dir, 'readme.txt'), 'w', encoding='utf-8') as f:
                f.write(readme_content)

            # Проверяем установку
            missing_files = check_installation(base_dir)
            if missing_files:
                logger.warning("\nWarning: Some files are missing:")
                for file in missing_files:
                    logger.warning(f"✗ {file}")
                return False

            logger.info("\n✓ Installation verified successfully!")
            logger.info(f"\nPortable version created in: {os.path.abspath(base_dir)}")
            if build_type == BUILD_TYPE_MACOS:
                logger.info("To start, run: chmod +x start.sh && ./start.sh")
            else:
                logger.info("To start, run start.bat in that folder")
            return True

    except Exception as e:
        logger.error(f"\nUnexpected error during build: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        os.chdir(original_dir)

if __name__ == "__main__":
    logger.info("Starting ComfyUI Launcher Portable build...")
    try:
        # Запрашиваем тип сборки
        build_type = select_build_type()
        
        # Проверяем совместимость системы и типа сборки
        system = platform.system()
        if build_type == BUILD_TYPE_MACOS and system != "Darwin":
            logger.error("MacOS build can only be created on MacOS!")
            sys.exit(1)
        elif build_type in [BUILD_TYPE_CUDA, BUILD_TYPE_DIRECTML] and system != "Windows":
            logger.error("Windows builds can only be created on Windows!")
            sys.exit(1)

        # Добавляем тип сборки к имени директории
        base_dir = f'ComfyUI-Launcher-Portable-{build_type.upper()}'
        
        success = build_portable(build_type)  # Передаем build_type как аргумент
        if not success:
            logger.warning("\nBuild completed with warnings!")
        else:
            logger.info("\nBuild successful!")
    except Exception as e:
        logger.error(f"\nError during build: {e}")
        import traceback
        traceback.print_exc()
    finally:
        input("\nPress Enter to exit...")