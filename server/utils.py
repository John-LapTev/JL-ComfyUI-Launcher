import json
import logging
import os
import time
import shutil
import socket
import requests
import hashlib
import unicodedata
import re
import subprocess
import threading
import tempfile
from tqdm import tqdm
from urllib.parse import urlparse
from settings import PROJECT_MAX_PORT, PROJECT_MIN_PORT, PROJECTS_DIR

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_url_structure(url):
    """Проверка структуры URL и автоматическая замена устаревших ссылок"""
    try:
        # Базовая проверка huggingface.co
        huggingface_pattern = r'^https://huggingface\.co/[\w-]+/[\w-]+/blob/[\w-]+\.(safetensors|bin|ckpt)$'
        if re.match(huggingface_pattern, url):
            # Добавляем проверку существования репозитория
            repo_path = "/".join(url.split("/")[3:5])
            api_url = f"https://huggingface.co/api/models/{repo_path}"
            try:
                response = requests.head(api_url)
                if response.status_code == 404:
                    logger.warning(f"Repository not found: {repo_path}")
                    return False
            except:
                # Если проверка не удалась, просто продолжаем
                pass
            return True
        
        # Базовая проверка civitai.com
        civitai_pattern = r'^https://civitai\.com/models/\d+$'
        if re.match(civitai_pattern, url):
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking URL structure: {e}")
        return False

def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')


COMFYUI_REPO_URL = "https://github.com/comfyanonymous/ComfyUI.git"

MAX_DOWNLOAD_ATTEMPTS = 3

CUSTOM_NODES_TO_IGNORE_FROM_SNAPSHOTS = ["ComfyUI-ComfyWorkflows", "ComfyUI-Manager"]

CW_ENDPOINT = os.environ.get("CW_ENDPOINT", "https://comfyworkflows.com")

CONFIG_FILEPATH = "./config.json"

DEFAULT_CONFIG = {
    "credentials": {
        "civitai": {
            "apikey": ""
        },
        "huggingface": {
            "token": ""
        }
    }
}

import os
from typing import List, Dict, Optional, Union
import json

class ModelFileWithNodeInfo:
    def __init__(self, filename: str, original_filepath: str, normalized_filepath: str):
        self.filename = filename
        self.original_filepath = original_filepath
        self.normalized_filepath = normalized_filepath

def convert_to_unix_path(path: str) -> str:
    return path.replace("\\\\", "/").replace("\\", "/")

def convert_to_windows_path(path: str) -> str:
    return path.replace("/", "\\")

def extract_model_file_names_with_node_info(json_data: Union[Dict, List], is_windows: bool = False) -> List[ModelFileWithNodeInfo]:
    file_names = []
    model_filename_extensions = {'.safetensors', '.ckpt', '.pt', '.pth', '.bin'}

    def recursive_search(data: Union[Dict, List, str], in_nodes: bool, node_type: Optional[str]):
        if isinstance(data, dict):
            for key, value in data.items():
                type_ = value.get('type') if isinstance(value, dict) else None
                recursive_search(value, key == 'nodes' if not in_nodes else in_nodes, type_ if in_nodes and not node_type else node_type)
        elif isinstance(data, list):
            for item in data:
                type_ = item.get('type') if isinstance(item, dict) else None
                recursive_search(item, in_nodes, type_ if in_nodes and not node_type else node_type)
        elif isinstance(data, str) and '.' in data:
            original_filepath = data
            normalized_filepath = convert_to_windows_path(original_filepath) if is_windows else convert_to_unix_path(original_filepath)
            filename = os.path.basename(data)

            if '.' + original_filepath.split('.')[-1] in model_filename_extensions:
                file_names.append(ModelFileWithNodeInfo(filename, original_filepath, normalized_filepath))

    recursive_search(json_data, False, None)
    return file_names


def print_process_output(process):
    try:
        for line in iter(process.stdout.readline, b''):
            try:
                print(line.decode('utf-8', errors='ignore'), end='')
            except Exception as e:
                try:
                    print(line.decode('cp1251', errors='ignore'), end='')
                except:
                    print("Failed to decode output line")
    except Exception as e:
        print(f"Error in print_process_output: {e}")

def run_command(cmd: List[str], cwd: Optional[str] = None, bg: bool = False) -> None:
    try:
        process = subprocess.Popen(
            " ".join(cmd),
            cwd=cwd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        if bg:
            return process.pid
            
        # Читаем вывод в реальном времени
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                logger.info(output.strip())
                
        retcode = process.poll()
        if retcode != 0:
            raise subprocess.CalledProcessError(retcode, cmd)
            
    except Exception as e:
        logger.error(f"Command failed: {' '.join(cmd)}")
        logger.error(f"Error: {str(e)}")
        raise

def get_ckpt_names_with_node_info(workflow_json: Union[Dict, List], is_windows: bool) -> List[ModelFileWithNodeInfo]:
    ckpt_names = []
    if isinstance(workflow_json, dict):
        ckpt_names = extract_model_file_names_with_node_info(workflow_json, is_windows)
    elif isinstance(workflow_json, list):
        for item in workflow_json:
            ckpt_names.extend(get_ckpt_names_with_node_info(item, is_windows))
    return ckpt_names

def normalize_model_filepaths_in_workflow_json(workflow_json: dict) -> dict:
    is_windows = os.name == "nt"
    ckpt_names = get_ckpt_names_with_node_info(workflow_json, is_windows)
    for ckpt_name in ckpt_names:
        workflow_json = json.dumps(workflow_json).replace(ckpt_name.original_filepath.replace("\\", "\\\\"), ckpt_name.normalized_filepath.replace("\\", "\\\\"))
        workflow_json = json.loads(workflow_json)
    return workflow_json


def run_command_in_project_venv(project_folder_path, command):
    if os.name == "nt":  # Check if running on Windows
        venv_activate = os.path.join(project_folder_path, "venv", "Scripts", "activate.bat")
    else:
        venv_activate = os.path.join(project_folder_path, "venv", "bin", "activate")
    
    assert os.path.exists(venv_activate), f"Virtualenv does not exist in project folder: {project_folder_path}"
    
    if os.name == "nt":
        command = ["call", venv_activate, "&&", command]
    else:
        command = [".", venv_activate, "&&", command]
    
    # Run the command using subprocess and capture stdout
    run_command(command)

def run_command_in_project_comfyui_venv(project_folder_path, command, in_bg=False):
    venv_activate = os.path.join(project_folder_path, "venv", "Scripts", "activate.bat") if os.name == "nt" else os.path.join(project_folder_path, "venv", "bin", "activate")
    comfyui_dir = os.path.join(project_folder_path, "comfyui")
    
    assert os.path.exists(venv_activate), f"Virtualenv does not exist in project folder: {project_folder_path}"

    if os.name == "nt":
        full_command = f"cmd /c \"{venv_activate} && cd /d {comfyui_dir} && {command}\""
        process = subprocess.Popen(full_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if in_bg:
            return process.pid
        else:
            print_process_output(process)
            return process.wait() == 0
    else:
        # Unix-like systems
        full_command = f". {venv_activate} && cd {comfyui_dir} && {command}"
        process = subprocess.Popen(full_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if in_bg:
            return process.pid
        else:
            print_process_output(process)
            return process.wait() == 0


def install_default_custom_nodes(project_folder_path, launcher_json=None):
    # install default custom nodes
    # comfyui-manager
    run_command(["git", "clone", f"https://github.com/ltdrdata/ComfyUI-Manager", os.path.join(project_folder_path, 'comfyui', 'custom_nodes', 'ComfyUI-Manager')])

    # pip install comfyui-manager
    run_command_in_project_venv(
        project_folder_path,
        f"pip install -r {os.path.join(project_folder_path, 'comfyui', 'custom_nodes', 'ComfyUI-Manager', 'requirements.txt')}",
    )

    run_command(["git", "clone", f"https://github.com/thecooltechguy/ComfyUI-ComfyWorkflows", os.path.join(project_folder_path, 'comfyui', 'custom_nodes', 'ComfyUI-ComfyWorkflows')])

    # pip install comfyui-comfyworkflows
    run_command_in_project_venv(
        project_folder_path,
        f"pip install -r {os.path.join(project_folder_path, 'comfyui', 'custom_nodes', 'ComfyUI-ComfyWorkflows', 'requirements.txt')}",
    )

def setup_initial_models_folder(models_folder_path):
    assert not os.path.exists(
        models_folder_path
    ), f"Models folder already exists: {models_folder_path}"
    
    tmp_dir = os.path.join(os.path.dirname(models_folder_path), "tmp_comfyui")
    run_command(["git", "clone", COMFYUI_REPO_URL, tmp_dir])

    shutil.move(os.path.join(tmp_dir, "models"), models_folder_path)
    shutil.rmtree(tmp_dir)


def is_launcher_json_format(import_json):
    if "format" in import_json and import_json["format"] == "comfyui_launcher":
        return True
    return False

def setup_custom_nodes_from_snapshot(project_folder_path, launcher_json):
    if not launcher_json:
        return
    for custom_node_repo_url, custom_node_repo_info in launcher_json["snapshot_json"][
        "git_custom_nodes"
    ].items():
        if any(
            [
                custom_node_to_ignore in custom_node_repo_url
                for custom_node_to_ignore in CUSTOM_NODES_TO_IGNORE_FROM_SNAPSHOTS
            ]
        ):
            continue

        custom_node_hash = custom_node_repo_info["hash"]
        custom_node_disabled = custom_node_repo_info["disabled"]
        if custom_node_disabled:
            continue
        custom_node_name = custom_node_repo_url.split("/")[-1].replace(".git", "")
        custom_node_path = os.path.join(
            project_folder_path, "comfyui", "custom_nodes", custom_node_name
        )
        
        # Clone the custom node repository
        run_command(["git", "clone", custom_node_repo_url, custom_node_path, "--recursive"])

        if custom_node_hash:
            # Checkout the specific hash
            run_command(["git", "checkout", custom_node_hash], cwd=custom_node_path)

        pip_requirements_path = os.path.join(custom_node_path, "requirements.txt")
        if os.path.exists(pip_requirements_path):
            run_command_in_project_venv(
                project_folder_path,
                f"pip install -r {os.path.join(custom_node_path, 'requirements.txt')}",
            )

        pip_requirements_post_path = os.path.join(custom_node_path, "requirements_post.txt")
        if os.path.exists(pip_requirements_post_path):
            run_command_in_project_venv(
                project_folder_path,
                f"pip install -r {os.path.join(custom_node_path, 'requirements_post.txt')}",
            )

        install_script_path = os.path.join(custom_node_path, "install.py")
        if os.path.exists(install_script_path):
            run_command_in_project_venv(project_folder_path, f"python {install_script_path}")

        # for ComfyUI-CLIPSeg, we need to separately copy the clipseg.py file from ComfyUI-CLIPSeg/custom_nodes into `project_folder_path/comfyui/custom_nodes
        if custom_node_name == "ComfyUI-CLIPSeg":
            clipseg_custom_node_file_path = os.path.join(custom_node_path, "custom_nodes", "clipseg.py")
            shutil.copy(clipseg_custom_node_file_path, os.path.join(project_folder_path, "comfyui", "custom_nodes", "clipseg.py"))

def compute_sha256_checksum(file_path):
    buf_size = 1024
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            data = f.read(buf_size)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest().lower()

def get_config():
    with open(CONFIG_FILEPATH, "r") as f:
        return json.load(f)
    
def update_config(config_update):
    config = get_config()
    config.update(config_update)
    with open(CONFIG_FILEPATH, "w") as f:
        json.dump(config, f)
    return config

def set_config(config):
    with open(CONFIG_FILEPATH, "w") as f:
        json.dump(config, f)

def download_with_retry(url, temp_path, dest_path, sha256_checksum=None, headers=None, max_retries=3):
    """Загрузка файла с повторными попытками и улучшенной обработкой ошибок"""
    if not url or not isinstance(url, str):
        logger.error(f"Invalid URL provided: {url}")
        return False

    # Добавляем базовые заголовки
    if headers is None:
        headers = {}
    headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive'
    })

    filename = os.path.basename(dest_path)
    logger.info(f"Starting download of {filename}")
    logger.debug(f"URL: {url}")

    # Создаем все необходимые директории заранее
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)

    for attempt in range(max_retries):
        current_temp_path = f"{temp_path}.{attempt}"
        try:
            # Получаем размер файла
            try:
                logger.info(f"Getting file info for {filename}...")
                head_response = requests.head(url, headers=headers, timeout=5)
                total_size = int(head_response.headers.get('content-length', 0))
                if total_size > 0:
                    logger.info(f"File size: {total_size/1024/1024:.1f} MB")
                else:
                    logger.info("File size unknown")
            except Exception as e:
                logger.warning(f"Failed to get file size: {str(e)}")
                total_size = 0

            # Загружаем файл
            logger.info(f"Downloading: {filename}")
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()

            block_size = 1024 * 1024  # 1MB chunks
            downloaded_size = 0
            start_time = time.time()
            last_update_time = start_time

            with open(current_temp_path, 'wb') as f:
                with tqdm(
                    total=total_size if total_size > 0 else None,
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=filename,
                    ascii=True,
                    ncols=100,
                    dynamic_ncols=True
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=block_size):
                        if chunk:
                            f.write(chunk)
                            chunk_size = len(chunk)
                            downloaded_size += chunk_size
                            pbar.update(chunk_size)

                            current_time = time.time()
                            if current_time - last_update_time >= 1:
                                elapsed = current_time - start_time
                                speed = downloaded_size / (1024 * 1024 * elapsed)
                                pbar.set_postfix({"Speed": f"{speed:.1f}MB/s"}, refresh=True)
                                last_update_time = current_time

            # Проверяем файл
            if not os.path.exists(current_temp_path):
                raise Exception("Downloaded file not found")

            file_size = os.path.getsize(current_temp_path)
            if file_size == 0:
                raise Exception("Downloaded file is empty")

            logger.info(f"Download completed: {filename}")
            logger.info(f"File size: {file_size/1024/1024:.1f} MB")

            # Проверяем контрольную сумму
            if sha256_checksum:
                logger.info("Verifying checksum...")
                if compute_sha256_checksum(current_temp_path) != sha256_checksum:
                    raise Exception("Checksum verification failed")

            # Перемещаем файл
            logger.info("Moving file to destination...")
            try:
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                shutil.move(current_temp_path, dest_path)
                
                if not os.path.exists(dest_path):
                    raise Exception("File verification after move failed")
                    
                return True
                
            except Exception as move_error:
                logger.error(f"Error moving file: {move_error}")
                if os.path.exists(current_temp_path):
                    try:
                        os.remove(current_temp_path)
                    except:
                        pass
                raise

        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
            if os.path.exists(current_temp_path):
                try:
                    os.remove(current_temp_path)
                except:
                    pass

            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            return False

    return False

def setup_files_from_launcher_json(project_folder_path, launcher_json):
    """Установка файлов из launcher.json с улучшенной обработкой ошибок"""
    if not launcher_json:
        return

    missing_download_files = set()
    config = get_config()
    
    try:
        logger.info("Starting file downloads...")
        total_files = sum(1 for file_infos in launcher_json.get("files", []))
        if total_files == 0:
            logger.info("No files to download")
            return missing_download_files

        logger.info(f"Total files to download: {total_files}")
        processed_files = 0

        # Создаем временную директорию для загрузок
        with tempfile.TemporaryDirectory() as temp_dir:
            for file_index, file_infos in enumerate(launcher_json.get("files", []), 1):
                current_file = None
                downloaded_file = False
                
                for file_info in file_infos:
                    if downloaded_file:
                        break

                    if not all(key in file_info for key in ["download_url", "dest_relative_path"]):
                        logger.warning(f"Incomplete file info: {file_info}")
                        continue
                        
                    download_url = file_info["download_url"]
                    dest_relative_path = file_info["dest_relative_path"]
                    current_file = dest_relative_path
                    sha256_checksum = file_info.get("sha256_checksum", "")

                    if not download_url or not isinstance(download_url, str):
                        logger.warning(f"Invalid or missing download URL for: {dest_relative_path}")
                        missing_download_files.add(dest_relative_path)
                        continue

                    dest_path = os.path.join(project_folder_path, "comfyui", dest_relative_path)
                    temp_path = os.path.join(temp_dir, os.path.basename(dest_relative_path))
                    
                    # Проверяем существующий файл
                    if os.path.exists(dest_path):
                        if sha256_checksum and compute_sha256_checksum(dest_path) == sha256_checksum:
                            logger.info(f"File already exists with correct checksum: {dest_path}")
                            downloaded_file = True
                            processed_files += 1
                            logger.info(f"Progress: {processed_files}/{total_files} files ({(processed_files/total_files*100):.0f}%)")
                            break
                        else:
                            logger.info(f"File exists but needs update: {dest_path}")

                    # Получаем URL для загрузки
                    download_urls = []
                    if "/comfyui-launcher/" in download_url:
                        try:
                            response = requests.get(download_url, timeout=30)
                            response.raise_for_status()
                            try:
                                response_json = response.json()
                                if "urls" in response_json and response_json["urls"]:
                                    download_urls = response_json["urls"]
                                else:
                                    download_urls = [download_url]
                            except (json.JSONDecodeError, ValueError):
                                logger.warning("Failed to parse JSON response, using direct URL")
                                download_urls = [download_url]
                        except requests.exceptions.RequestException as e:
                            if hasattr(e.response, 'status_code') and e.response.status_code == 500:
                                logger.warning(f"Server error (500) for URL {download_url}")
                                continue
                            logger.error(f"Error getting download URLs: {e}")
                            download_urls = [download_url]
                    else:
                        download_urls = [download_url]

                    # Пробуем загрузить файл
                    for url in download_urls:
                        if not url or not isinstance(url, str):
                            continue

                        headers = {}
                        # Добавляем авторизационные заголовки
                        if "civitai.com" in url:
                            api_key = config.get('credentials', {}).get('civitai', {}).get('apikey')
                            if api_key:
                                headers["Authorization"] = f"Bearer {api_key}"
                        elif "huggingface.co" in url:
                            hf_token = config.get('credentials', {}).get('huggingface', {}).get('token')
                            if hf_token:
                                headers["Authorization"] = f"Bearer {hf_token}"
                        
                        # Пробуем загрузить файл
                        if download_with_retry(
                            url=url,
                            temp_path=temp_path,
                            dest_path=dest_path,
                            sha256_checksum=sha256_checksum,
                            headers=headers
                        ):
                            downloaded_file = True
                            processed_files += 1
                            logger.info(f"Progress: {processed_files}/{total_files} files ({(processed_files/total_files*100):.0f}%)")
                            break

                if not downloaded_file and current_file:
                    logger.warning(f"Failed to download: {current_file}")
                    missing_download_files.add(current_file)
                    processed_files += 1
                    logger.info(f"Progress: {processed_files}/{total_files} files ({(processed_files/total_files*100):.0f}%)")

        logger.info(f"Download completed. Success: {total_files - len(missing_download_files)}, Failed: {len(missing_download_files)}")
        if missing_download_files:
            for missing in missing_download_files:
                logger.warning(f"Missing file: {missing}")
                
        return missing_download_files

    except Exception as e:
        logger.error(f"Error in setup_files_from_launcher_json: {e}")
        logger.error("Stack trace:", exc_info=True)
        return missing_download_files

def get_launcher_json_for_workflow_json(workflow_json, resolved_missing_models, skip_model_validation):
    try:
        # Преобразуем skip_model_validation в строку "true"/"false" для URL
        skip_validation = str(skip_model_validation).lower()
        
        # Формируем данные запроса
        request_data = {
            "workflow": workflow_json,
            "isWindows": os.name == "nt",
            "resolved_missing_models": resolved_missing_models,
            "skipModelValidation": skip_model_validation  # Добавляем в тело запроса
        }
        
        response = requests.post(
            f"{CW_ENDPOINT}/api/comfyui-launcher/setup_workflow_json?skipModelValidation={skip_validation}",
            json=request_data,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 400:
            response_data = response.json()
            # Проверяем, действительно ли это пропуск моделей
            if skip_model_validation and "missing_models" in response_data:
                # Если пропускаем валидацию, возвращаем workflow как есть
                return {
                    "success": True,
                    "launcher_json": {
                        "workflow_json": workflow_json,
                        "files": [],  # Пустой список файлов
                        "snapshot_json": {"comfyui": None, "git_custom_nodes": {}},
                        "pip_requirements": []
                    }
                }
            return response_data
        else:
            raise Exception(f"Server returned status code: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Error in get_launcher_json_for_workflow_json: {str(e)}")
        raise

def generate_incrementing_filename(filepath):
    filename, file_extension = os.path.splitext(filepath)
    counter = 1
    while os.path.exists(filepath):
        filepath = f"{filename} ({counter}){file_extension}"
        counter += 1
    return filepath

def rename_file_in_workflow_json(workflow_json, old_filename, new_filename):
    workflow_json_str = json.dumps(workflow_json)
    workflow_json_str = workflow_json_str.replace(old_filename, new_filename)
    return json.loads(workflow_json_str)

def rename_file_in_launcher_json(launcher_json, old_filename, new_filename):
    workflow_json = launcher_json["workflow_json"]
    workflow_json_str = json.dumps(workflow_json)
    workflow_json_str = workflow_json_str.replace(old_filename, new_filename)
    workflow_json = json.loads(workflow_json_str)
    launcher_json["workflow_json"] = workflow_json


def set_default_workflow_from_launcher_json(project_folder_path, launcher_json):
    """
    Устанавливает workflow по умолчанию из launcher.json с поддержкой разных форматов
    
    Args:
        project_folder_path (str): Путь к папке проекта
        launcher_json (dict): JSON с конфигурацией launcher'а
    """
    try:
        if not launcher_json or "workflow_json" not in launcher_json:
            logger.warning("Нет workflow_json в launcher_json")
            return

        # Получаем workflow_json и обрабатываем разные форматы
        workflow_json = launcher_json["workflow_json"]
        
        # Проверяем формат с вложенным workflow
        if isinstance(workflow_json, dict) and "workflow" in workflow_json:
            logger.info("Обнаружен вложенный формат workflow")
            workflow_json = workflow_json["workflow"]
        
        # Проверяем базовую структуру
        if not isinstance(workflow_json, dict):
            workflow_json = {}
            logger.warning("workflow_json не является словарем, создаем пустую структуру")
            
        # Устанавливаем обязательные поля
        workflow_json["version"] = float(workflow_json.get("version", 1.0))
        workflow_json.setdefault("nodes", [])
        workflow_json.setdefault("links", [])
        
        # Пересчитываем ID для узлов и связей
        max_node_id = 0
        max_link_id = 0
        
        for node in workflow_json.get("nodes", []):
            if isinstance(node, dict) and "id" in node:
                try:
                    node_id = int(str(node["id"]).strip())
                    max_node_id = max(max_node_id, node_id)
                except (ValueError, TypeError):
                    continue
        
        for link in workflow_json.get("links", []):
            if isinstance(link, dict) and "id" in link:
                try:
                    link_id = int(str(link["id"]).strip())
                    max_link_id = max(max_link_id, link_id)
                except (ValueError, TypeError):
                    continue
                
        # Устанавливаем ID счетчики
        workflow_json["last_node_id"] = max_node_id
        workflow_json["last_link_id"] = max_link_id

        # Сохраняем в defaultGraph.js
        default_graph_path = os.path.join(
            project_folder_path, "comfyui", "web", "scripts", "defaultGraph.js"
        )
        os.makedirs(os.path.dirname(default_graph_path), exist_ok=True)
        
        with open(default_graph_path, "w", encoding='utf-8') as f:
            f.write("window.resetWorkflowHistory = true;\n")
            f.write(f"export const defaultGraph = {json.dumps(workflow_json, indent=2, ensure_ascii=False)};")
        logger.info(f"Сохранен defaultGraph.js с {len(workflow_json.get('nodes', []))} узлами")

        # Сохраняем в current_graph.json
        workflow_path = os.path.join(
            project_folder_path, "comfyui", "custom_nodes", "ComfyUI-ComfyWorkflows", "current_graph.json"
        )
        os.makedirs(os.path.dirname(workflow_path), exist_ok=True)
        
        with open(workflow_path, "w", encoding='utf-8') as f:
            json.dump(workflow_json, f, indent=2, ensure_ascii=False)
        logger.info(f"Сохранен current_graph.json")

    except Exception as e:
        logger.error(f"Ошибка при установке workflow: {str(e)}")
        logger.debug("Workflow JSON:", workflow_json if 'workflow_json' in locals() else "Недоступен")
        raise


def get_launcher_state(project_folder_path):
    state = {}
    launcher_folder_path = os.path.join(project_folder_path, ".launcher")
    os.makedirs(launcher_folder_path, exist_ok=True)

    state_path = os.path.join(launcher_folder_path, "state.json")

    if os.path.exists(state_path):
        with open(state_path, "r") as f:
            state = json.load(f)

    return state, state_path


def set_launcher_state_data(project_folder_path, data: dict):
    launcher_folder_path = os.path.join(project_folder_path, ".launcher")
    os.makedirs(launcher_folder_path, exist_ok=True)

    existing_state, existing_state_path = get_launcher_state(project_folder_path)
    existing_state.update(data)

    with open(existing_state_path, "w") as f:
        json.dump(existing_state, f)

def install_pip_reqs(project_folder_path, pip_reqs):
    """Установка pip зависимостей"""
    if not pip_reqs:
        return
    
    logger.info("Installing pip requirements...")
    
    # Создаем временный requirements.txt
    requirements_path = os.path.join(project_folder_path, "requirements.txt")
    with open(requirements_path, "w") as f:
        for req in pip_reqs:
            if isinstance(req, str):
                f.write(req + "\n")
            elif isinstance(req, dict):
                f.write(f"{req['_key']}=={req['_version']}\n")
    
    try:
        # Сначала пробуем установить без конфликтующих пакетов
        logger.info("Attempting to install requirements...")
        run_command_in_project_venv(
            project_folder_path,
            f"pip install -r {requirements_path} --no-deps",
        )
        
        # Затем устанавливаем зависимости с игнорированием конфликтов
        logger.info("Installing dependencies...")
        run_command_in_project_venv(
            project_folder_path,
            f"pip install -r {requirements_path} --no-dependencies",
        )
        
        # Устанавливаем typing-extensions отдельно с совместимой версией
        logger.info("Installing typing-extensions...")
        run_command_in_project_venv(
            project_folder_path,
            "pip install typing-extensions>=4.8.0",
        )
        
    except Exception as e:
        logger.error(f"Error installing requirements: {e}")
        # Если установка с --no-deps не сработала, пробуем установить с --ignore-installed
        try:
            logger.info("Retrying installation with --ignore-installed...")
            run_command_in_project_venv(
                project_folder_path,
                f"pip install -r {requirements_path} --ignore-installed",
            )
        except Exception as e:
            logger.error(f"Failed to install requirements: {e}")
            raise
    finally:
        # Удаляем временный файл
        if os.path.exists(requirements_path):
            os.remove(requirements_path)

def get_project_port(id):
    project_path = os.path.join(PROJECTS_DIR, id)
    if os.path.exists(os.path.join(project_path, "port.txt")):
        with open(os.path.join(project_path, "port.txt"), "r") as f:
            return int(f.read().strip())
    return find_free_port(PROJECT_MIN_PORT, PROJECT_MAX_PORT)

def is_port_in_use(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0
    
def find_free_port(start_port, end_port):
    for port in range(start_port, end_port + 1):
        with socket.socket() as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                pass  # Port is already in use, try the next one
    return None  # No free port found in the range

def create_symlink(source, target):
    try:
        source = os.path.abspath(source)
        target = os.path.abspath(target)
        
        logger.info(f"Creating symlink/copy: {source} -> {target}")
        
        if os.path.exists(target):
            logger.info(f"Target path already exists: {target}")
            return
            
        if os.name == 'nt':  # Windows
            try:
                # Используем os.system вместо subprocess для лучшей совместимости
                result = os.system(f'cmd /c mklink /D "{target}" "{source}"')
                if result == 0:
                    logger.info(f"Created symlink: {target} -> {source}")
                    return
                else:
                    raise Exception(f"Failed to create symlink, return code: {result}")
            except Exception as e:
                logger.warning(f"Failed to create symlink: {e}, falling back to copy")
                shutil.copytree(source, target)
                logger.info(f"Copied directory: {source} -> {target}")
        else:  # Linux/Mac
            try:
                os.symlink(source, target, target_is_directory=True)
                logger.info(f"Created symlink: {target} -> {source}")
            except OSError as e:
                logger.warning(f"Failed to create symlink: {e}, falling back to copy")
                shutil.copytree(source, target)
                logger.info(f"Copied directory: {source} -> {target}")
    except Exception as e:
        logger.error(f"Error creating symlink/copy: {e}")
        try:
            shutil.copytree(source, target)
            logger.info(f"Copied directory as fallback: {source} -> {target}")
        except Exception as copy_error:
            logger.error(f"Error copying directory: {copy_error}")
            raise

def create_virtualenv(venv_path):
    """Создание виртуального окружения с корректной обработкой отмены"""
    cleanup_needed = False
    try:
        logger.info(f"Creating virtual environment at {venv_path}")
        
        venv_path = os.path.abspath(venv_path)
        cleanup_needed = True
        
        if os.path.exists(venv_path):
            logger.info(f"Virtual environment already exists at {venv_path}")
            return

        # Устанавливаем virtualenv
        logger.info("Installing virtualenv...")
        try:
            subprocess.run([
                "pip", "install", "virtualenv"
            ], check=True)
        except subprocess.CalledProcessError as e:
            logger.warning(f"virtualenv installation warning: {e}")
            # Продолжаем, так как virtualenv может уже быть установлен

        # Создаем виртуальное окружение
        logger.info("Creating virtual environment...")
        try:
            subprocess.run([
                "virtualenv", venv_path
            ], check=True)
        except KeyboardInterrupt:
            logger.info("Operation cancelled by user during virtualenv creation")
            raise
        except Exception as e:
            logger.error(f"Error creating virtualenv: {e}")
            raise

        # Определяем пути
        if os.name == "nt":  # Windows
            python_path = os.path.join(venv_path, 'Scripts', 'python.exe')
            pip_path = os.path.join(venv_path, 'Scripts', 'pip.exe')
        else:  # Linux/Mac
            python_path = os.path.join(venv_path, 'bin', 'python')
            pip_path = os.path.join(venv_path, 'bin', 'pip')

        # Обновляем pip
        logger.info("Updating pip...")
        try:
            subprocess.run([
                python_path, '-m', 'pip', 'install', '--upgrade', 'pip'
            ], check=True)
        except KeyboardInterrupt:
            logger.info("Operation cancelled by user during pip upgrade")
            raise
        except Exception as e:
            logger.warning(f"Pip upgrade warning: {e}")
            # Продолжаем, так как это некритичная ошибка

        # Устанавливаем PyTorch
        logger.info("Installing PyTorch...")
        try:
            subprocess.run([
                pip_path,
                'install',
                '--no-cache-dir',  # Избегаем проблем с кешем
                'torch',
                'torchvision',
                'torchaudio',
                '--index-url', 'https://download.pytorch.org/whl/cu121'
            ], check=True)
        except KeyboardInterrupt:
            logger.info("Operation cancelled by user during PyTorch installation")
            raise
        except Exception as e:
            logger.error(f"PyTorch installation error: {e}")
            raise

        cleanup_needed = False
        logger.info("Virtual environment created successfully")
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        if cleanup_needed and os.path.exists(venv_path):
            logger.info("Cleaning up virtual environment...")
            try:
                shutil.rmtree(venv_path, ignore_errors=True)
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
        raise
        
    except Exception as e:
        logger.error(f"Error creating virtual environment: {e}")
        if cleanup_needed and os.path.exists(venv_path):
            logger.info("Cleaning up virtual environment...")
            try:
                shutil.rmtree(venv_path, ignore_errors=True)
            except Exception as cleanup_error:
                logger.error(f"Error during cleanup: {cleanup_error}")
        raise