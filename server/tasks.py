import json
import os
import shutil
from celery import shared_task
import logging
from utils import COMFYUI_REPO_URL, create_symlink, create_virtualenv, install_default_custom_nodes, install_pip_reqs, normalize_model_filepaths_in_workflow_json, run_command, run_command_in_project_venv, set_default_workflow_from_launcher_json, set_launcher_state_data, setup_custom_nodes_from_snapshot, setup_files_from_launcher_json, setup_initial_models_folder

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@shared_task(ignore_result=False, bind=True)
def create_comfyui_project(
    self, project_folder_path, models_folder_path, id, name, launcher_json=None, port=None, create_project_folder=True
):
    logger.info(f"Starting task create_comfyui_project with id: {id}, name: {name}")
    logger.info(f"Project path: {project_folder_path}")
    logger.info(f"Models path: {models_folder_path}")

    project_folder_path = os.path.abspath(project_folder_path)
    models_folder_path = os.path.abspath(models_folder_path)

    try:
        if create_project_folder:
            logger.info(f"Creating project folder: {project_folder_path}")
            if os.path.exists(project_folder_path):
                logger.warning(f"Project folder already exists, removing: {project_folder_path}")
                shutil.rmtree(project_folder_path, ignore_errors=True)
            os.makedirs(project_folder_path)
        else:
            logger.info(f"Using existing project folder: {project_folder_path}")
            if not os.path.exists(project_folder_path):
                logger.info(f"Creating project folder as it doesn't exist: {project_folder_path}")
                os.makedirs(project_folder_path)

        set_launcher_state_data(
            project_folder_path,
            {"id":id,"name":name, "status_message": "Downloading ComfyUI...", "state": "download_comfyui"},
        )
        logger.info("Cloning ComfyUI repository")
        run_command(
            ["git", "clone", COMFYUI_REPO_URL, os.path.join(project_folder_path, 'comfyui')],
        )

        if launcher_json:
            logger.info("Processing launcher_json configuration")
            comfyui_commit_hash = launcher_json["snapshot_json"]["comfyui"]
            if comfyui_commit_hash:
                logger.info(f"Checking out commit: {comfyui_commit_hash}")
                run_command(
                    ["git", "checkout", comfyui_commit_hash],
                    cwd=os.path.join(project_folder_path, 'comfyui'),
                )
            launcher_json['workflow_json'] = normalize_model_filepaths_in_workflow_json(launcher_json['workflow_json'])

        logger.info("Setting up web interface files")
        os.rename(
            os.path.join(project_folder_path, "comfyui", "web", "index.html"),
            os.path.join(project_folder_path, "comfyui", "web", "comfyui_index.html"),
        )

        web_frame_path = os.path.join("web", "comfy_frame.html")
        logger.info(f"Copying frame file from: {web_frame_path}")
        shutil.copy(
            web_frame_path,
            os.path.join(project_folder_path, "comfyui", "web", "index.html"),
        )

        if os.path.exists(os.path.join(project_folder_path, "comfyui", "models")):
            logger.info("Removing existing models directory")
            shutil.rmtree(
                os.path.join(project_folder_path, "comfyui", "models"), ignore_errors=True
            )

        if not os.path.exists(models_folder_path):
            logger.info("Setting up initial models folder")
            setup_initial_models_folder(models_folder_path)

        logger.info("Creating models symlink")
        create_symlink(models_folder_path, os.path.join(project_folder_path, "comfyui", "models"))

        set_launcher_state_data(
            project_folder_path,
            {"status_message": "Installing ComfyUI...", "state": "install_comfyui"},
        )

        logger.info("Creating virtual environment")
        create_virtualenv(os.path.join(project_folder_path, 'venv'))

        logger.info("Installing ComfyUI requirements")
        run_command_in_project_venv(
            project_folder_path,
            f"pip install -r {os.path.join(project_folder_path, 'comfyui', 'requirements.txt')}",
        )

        set_launcher_state_data(
            project_folder_path,
            {
                "status_message": "Installing custom nodes...",
                "state": "install_custom_nodes",
            },
        )

        logger.info("Installing custom nodes")
        install_default_custom_nodes(project_folder_path, launcher_json)
        setup_custom_nodes_from_snapshot(project_folder_path, launcher_json)

        if launcher_json and "pip_requirements" in launcher_json:
            logger.info("Installing additional pip requirements")
            install_pip_reqs(project_folder_path, launcher_json["pip_requirements"])

        set_launcher_state_data(
            project_folder_path,
            {
                "status_message": "Downloading models & other files...",
                "state": "download_files",
            },
        )

        logger.info("Setting up files from launcher json")
        setup_files_from_launcher_json(project_folder_path, launcher_json)
        set_default_workflow_from_launcher_json(project_folder_path, launcher_json)

        if launcher_json:
            logger.info("Saving launcher.json")
            with open(os.path.join(project_folder_path, "launcher.json"), "w") as f:
                json.dump(launcher_json, f)

        if port is not None:
            logger.info(f"Setting port: {port}")
            with open(os.path.join(project_folder_path, "port.txt"), "w") as f:
                f.write(str(port))

        set_launcher_state_data(
            project_folder_path, {"status_message": "Ready", "state": "ready"}
        )
        logger.info("Project creation completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error creating project: {str(e)}", exc_info=True)
        try:
            # Пробуем установить статус ошибки
            set_launcher_state_data(
                project_folder_path, 
                {
                    "status_message": f"Error: {str(e)}", 
                    "state": "error"
                }
            )
        except:
            pass
        raise