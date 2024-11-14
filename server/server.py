import json
import shutil
import signal
import subprocess
import stat
import time
import torch
import logging
from flask import Flask, jsonify, request, render_template
from showinfm import show_in_file_manager
from settings import ALLOW_OVERRIDABLE_PORTS_PER_PROJECT, CELERY_BROKER_DIR, CELERY_RESULTS_DIR, PROJECT_MAX_PORT, PROJECT_MIN_PORT, PROJECTS_DIR, MODELS_DIR, PROXY_MODE, SERVER_PORT, TEMPLATES_DIR
import requests
import os, psutil, sys
from utils import (
    CONFIG_FILEPATH,
    DEFAULT_CONFIG,
    get_config,
    get_launcher_json_for_workflow_json,
    get_launcher_state,
    get_project_port,
    is_launcher_json_format,
    is_port_in_use,
    run_command,
    run_command_in_project_comfyui_venv,
    set_config,
    set_launcher_state_data,
    slugify,
    update_config,
    check_url_structure
)
from celery import Celery, Task
from tasks import create_comfyui_project

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app

CW_ENDPOINT = os.environ.get("CW_ENDPOINT", "https://comfyworkflows.com")

app = Flask(
    __name__, static_url_path="", static_folder="../web/dist", template_folder="../web/dist"
)
app.config.from_mapping(
    CELERY=dict(
        broker_url='redis://localhost:6379/0',
        result_backend='redis://localhost:6379/0',
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        task_ignore_result=False,
        task_always_eager=False,
        broker_connection_retry=True,
        broker_connection_retry_on_startup=True,
        # Добавляем эти две строки:
        worker_redirect_stdouts=False,
        worker_redirect_stdouts_level='INFO'
    ),
)
celery_app = celery_init_app(app)

@app.route("/api/open_models_folder")
def open_models_folder():
    show_in_file_manager(MODELS_DIR)
    return ""

@app.route("/api/settings")
def api_settings():
    return jsonify({
        "PROJECT_MIN_PORT": PROJECT_MIN_PORT,
        "PROJECT_MAX_PORT": PROJECT_MAX_PORT,
        "ALLOW_OVERRIDABLE_PORTS_PER_PROJECT": ALLOW_OVERRIDABLE_PORTS_PER_PROJECT,
        "PROXY_MODE": PROXY_MODE
    })

@app.route("/api/projects", methods=["GET"])
def list_projects():
    projects = []
    for proj_folder in os.listdir(PROJECTS_DIR):
        full_proj_path = os.path.join(PROJECTS_DIR, proj_folder)
        if not os.path.isdir(full_proj_path):
            continue
        launcher_state, _ = get_launcher_state(full_proj_path)
        if not launcher_state:
            continue
        project_port = get_project_port(proj_folder)
        projects.append(
            {
                "id": proj_folder,
                "state": launcher_state,
                "project_folder_name": proj_folder,
                "project_folder_path": full_proj_path,
                "last_modified": os.stat(full_proj_path).st_mtime,
                "port" : project_port
            }
        )

    projects.sort(key=lambda x: x["last_modified"], reverse=True)
    return jsonify(projects)

@app.route("/api/projects/<id>", methods=["GET"])
def get_project(id):
    project_path = os.path.join(PROJECTS_DIR, id)
    assert os.path.exists(project_path), f"Project with id {id} does not exist"
    launcher_state, _ = get_launcher_state(project_path)
    project_port = get_project_port(id)
    return jsonify(
        {
            "id": id,
            "state": launcher_state,
            "project_folder_name": id,
            "project_folder_path": project_path,
            "last_modified": os.stat(project_path).st_mtime,
            "port" : project_port
        }
    )

@app.route("/api/get_config", methods=["GET"])
def api_get_config():
    config = get_config()
    return jsonify(config)

@app.route("/api/update_config", methods=["POST"])
def api_update_config():
    request_data = request.get_json()
    update_config(request_data)
    return jsonify({"success": True})

@app.route("/api/set_config", methods=["POST"])
def api_set_config():
    request_data = request.get_json()
    set_config(request_data)
    return jsonify({"success": True})
    
@app.route("/api/create_project", methods=["POST"])
def create_project():
    try:
        request_data = request.get_json()
        name = request_data["name"]
        template_id = request_data.get("template_id", "empty")
        port = request_data.get("port")

        id = slugify(name)
        project_path = os.path.join(PROJECTS_DIR, id)
        
        logger.info(f"Creating project with id {id} and name {name} from template {template_id}")
        assert not os.path.exists(project_path), f"Project with id {id} already exists"

        models_path = MODELS_DIR
        launcher_json = None
        
        # Получение launcher_json из шаблона
        template_folder = os.path.join(TEMPLATES_DIR, template_id)
        template_launcher_json_fp = os.path.join(template_folder, "launcher.json")
        
        if os.path.exists(template_launcher_json_fp):
            with open(template_launcher_json_fp, "r") as f:
                launcher_json = json.load(f)
        else:
            template_workflow_json_fp = os.path.join(template_folder, "workflow.json")
            if os.path.exists(template_workflow_json_fp):
                with open(template_workflow_json_fp, "r") as f:
                    template_workflow_json = json.load(f)
                res = get_launcher_json_for_workflow_json(
                    template_workflow_json, 
                    resolved_missing_models=[], 
                    skip_model_validation=True
                )
                if (res["success"] and res["launcher_json"]):
                    launcher_json = res["launcher_json"]
                else:
                    return jsonify({ 
                        "success": False, 
                        "missing_models": [], 
                        "error": res["error"] 
                    })

        # Создание директории проекта и установка начального состояния
        os.makedirs(project_path)
        set_launcher_state_data(
            project_path,
            {
                "id": id,
                "name": name, 
                "status_message": "Initializing project...", 
                "state": "initializing"
            },
        )

        # Создание и запуск Celery задачи
        logger.info(f"Creating Celery task for project {id}")
        task = create_comfyui_project.apply_async(
            args=[project_path, models_path],
            kwargs={
                "id": id,
                "name": name,
                "launcher_json": launcher_json,
                "port": port,
                "create_project_folder": False
            }
        )
        logger.info(f"Celery task created with ID: {task.id}")

        # Сохранение ID задачи
        with open(os.path.join(project_path, "setup_task_id.txt"), "w") as f:
            f.write(task.id)

        return jsonify({"success": True, "id": id, "task_id": task.id})

    except Exception as e:
        logger.error(f"Error creating project: {str(e)}", exc_info=True)
        if os.path.exists(project_path):
            shutil.rmtree(project_path, ignore_errors=True)
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/import_project", methods=["POST"])
def import_project():
    try:
        request_data = request.get_json()
        name = request_data["name"]
        import_json = request_data["import_json"]
        resolved_missing_models = request_data["resolved_missing_models"]
        skipping_model_validation = request_data["skipping_model_validation"]
        port = request_data.get("port")

        id = slugify(name)
        project_path = os.path.join(PROJECTS_DIR, id)
        assert not os.path.exists(project_path), f"Project with id {id} already exists"

        models_path = MODELS_DIR

        if is_launcher_json_format(import_json):
            logger.info("Detected launcher json format")
            launcher_json = import_json
        else:
            logger.info("Detected workflow json format, converting to launcher json format")
            skip_model_validation = True if skipping_model_validation else False
            
            if len(resolved_missing_models) > 0:
                for model in resolved_missing_models:
                    if (model["filename"] is None or model["node_type"] is None or model["dest_relative_path"] is None):
                        return jsonify({ "success": False, "error": f"one of the resolved models has an empty filename, node type, or destination path. please try again." })
                    elif (model["source"]["url"] is not None and model["source"]["file_id"] is None):
                        is_valid = check_url_structure(model["source"]["url"])
                        if (is_valid is False):
                            return jsonify({ "success": False, "error": f"the url f{model['source']['url']} is invalid. please make sure it is a link to a model file on huggingface or a civitai model." })
                    elif (model["source"]["file_id"] is None and model["source"]["url"] is None):
                        return jsonify({ "success": False, "error": f"you didn't select one of the suggestions (or import a url) for the following missing file: {model['filename']}" })
                skip_model_validation = True

            res = get_launcher_json_for_workflow_json(import_json, resolved_missing_models, skip_model_validation)
            if (res["success"] and res["launcher_json"]):
                launcher_json = res["launcher_json"]
            elif (res["success"] is False and res["error"] == "MISSING_MODELS" and len(res["missing_models"]) > 0):
                return jsonify({ "success": False, "missing_models": res["missing_models"], "error": res["error"] })
            else:
                logger.error(f"Error getting launcher json: {res}")
                return jsonify({ "success": False, "error": res["error"] })
            
        logger.info(f"Creating project with id {id} and name {name} from imported json")
        
        os.makedirs(project_path)
        set_launcher_state_data(
            project_path,
            {
                "id": id,
                "name": name, 
                "status_message": "Initializing imported project...", 
                "state": "initializing"
            },
        )

        task = create_comfyui_project.apply_async(
            args=[project_path, models_path],
            kwargs={
                "id": id,
                "name": name,
                "launcher_json": launcher_json,
                "port": port,
                "create_project_folder": False
            }
        )
        logger.info(f"Created import task with ID: {task.id}")

        with open(os.path.join(project_path, "setup_task_id.txt"), "w") as f:
            f.write(task.id)
        
        return jsonify({"success": True, "id": id}) 

    except Exception as e:
        logger.error(f"Error importing project: {str(e)}", exc_info=True)
        if os.path.exists(project_path):
            shutil.rmtree(project_path, ignore_errors=True)
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/projects/<id>/start", methods=["POST"])
def start_project(id):
    project_path = os.path.join(PROJECTS_DIR, id)
    assert os.path.exists(project_path), f"Project with id {id} does not exist"

    launcher_state, _ = get_launcher_state(project_path)
    assert launcher_state
    assert launcher_state["state"] == "ready", f"Project with id {id} is not ready yet"

    port = get_project_port(id)
    assert port, "No free port found"
    assert not is_port_in_use(port), f"Port {port} is already in use"

    # Получаем абсолютные пути
    comfyui_path = os.path.abspath(os.path.join(project_path, "comfyui"))
    venv_python = os.path.abspath(os.path.join(project_path, "venv", "Scripts", "python.exe"))
    
    logger.info(f"Starting ComfyUI for project {id}")
    logger.info(f"ComfyUI path: {comfyui_path}")
    logger.info(f"Python path: {venv_python}")
    
    # Проверяем GPU
    mps_available = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    if not torch.cuda.is_available() and not mps_available:
        logger.warning("No GPU/MPS detected, launching ComfyUI with CPU...")
        gpu_flag = " --cpu"
    else:
        gpu_flag = ""
    
    # Создаем bat файл для запуска проекта
    start_bat_content = f'''@echo off
cd /d "{comfyui_path}"
call "{os.path.join(project_path, "venv", "Scripts", "activate.bat")}"
"{venv_python}" main.py --port {port} --listen 0.0.0.0{gpu_flag}
pause
'''
    start_bat_path = os.path.join(project_path, f"start_{id}.bat")
    with open(start_bat_path, 'w') as f:
        f.write(start_bat_content)
    
    # Запускаем процесс через subprocess
    try:
        # Создаем команду запуска
        cmd = f'cmd /c "cd /d "{comfyui_path}" && "{venv_python}" main.py --port {port} --listen 0.0.0.0{gpu_flag}"'
        logger.info(f"Executing command: {cmd}")
        
        # Запускаем в новом окне
        process = subprocess.Popen(
            cmd,
            shell=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        
        pid = process.pid
        logger.info(f"Started process with PID: {pid}")
        
        # Ждем пока порт станет доступен
        max_wait_secs = 60
        while max_wait_secs > 0:
            if is_port_in_use(port):
                break
            time.sleep(1)
            max_wait_secs -= 1
        
        if max_wait_secs <= 0:
            logger.warning(f"Timeout waiting for port {port} to become available")
        
        # Обновляем состояние
        set_launcher_state_data(
            project_path,
            {
                "state": "running",
                "status_message": "Running...",
                "port": port,
                "pid": pid
            }
        )
        
        return jsonify({"success": True, "port": port})
        
    except Exception as e:
        logger.error(f"Error starting project: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/projects/<id>/stop", methods=["POST"])
def stop_project(id):
    project_path = os.path.join(PROJECTS_DIR, id)
    assert os.path.exists(project_path), f"Project with id {id} does not exist"

    launcher_state, _ = get_launcher_state(project_path)
    assert launcher_state

    assert launcher_state["state"] == "running", f"Project with id {id} is not running"

    try:
        pid = launcher_state["pid"]
        parent_pid = pid
        parent = psutil.Process(parent_pid)
        for child in parent.children(recursive=True):
            child.terminate()
        parent.terminate()
    except:
        pass

    set_launcher_state_data(project_path, {"state": "ready", "status_message" : "Ready", "port": None, "pid": None})
    return jsonify({"success": True})

@app.route("/api/projects/<id>/delete", methods=["POST"])
def delete_project(id):
    project_path = os.path.join(PROJECTS_DIR, id)
    assert os.path.exists(project_path), f"Project with id {id} does not exist"

    setup_task_id_fp = os.path.join(project_path, "setup_task_id.txt")
    if os.path.exists(setup_task_id_fp):
        with open(setup_task_id_fp, "r") as f:
            setup_task_id = f.read()
            if setup_task_id:
                try:
                    celery_app.control.revoke(setup_task_id, terminate=True)
                except:
                    pass

    launcher_state, _ = get_launcher_state(project_path)
    if launcher_state and launcher_state["state"] == "running":
        stop_project(id)

    try:
        # Сначала пытаемся удалить обычным способом
        shutil.rmtree(project_path, ignore_errors=True)
        
        # Если папка все еще существует, используем принудительное удаление
        if os.path.exists(project_path):
            def on_rm_error(func, path, exc_info):
                # Делаем файл доступным для записи
                os.chmod(path, stat.S_IWRITE)
                func(path)  # Пробуем удалить снова
                
            # Сначала делаем все файлы доступными для записи
            for root, dirs, files in os.walk(project_path):
                for dir in dirs:
                    os.chmod(os.path.join(root, dir), stat.S_IWRITE)
                for file in files:
                    os.chmod(os.path.join(root, file), stat.S_IWRITE)
                    
            # Пытаемся удалить еще раз с обработчиком ошибок
            shutil.rmtree(project_path, onerror=on_rm_error)
            
        # Проверяем, что папка действительно удалена
        if os.path.exists(project_path):
            logger.warning(f"Failed to delete project directory: {project_path}")
            return jsonify({"success": False, "error": "Failed to delete project directory"}), 500
            
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

    return jsonify({"success": True})

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
@app.errorhandler(404)
def index(path):
    return render_template("index.html")

if __name__ == "__main__":
    logger.info("Starting ComfyUI Launcher...")
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILEPATH):
        set_config(DEFAULT_CONFIG)
    logger.info(f"Open http://localhost:{SERVER_PORT} in your browser.")
    app.run(host="0.0.0.0", debug=False, port=SERVER_PORT)    