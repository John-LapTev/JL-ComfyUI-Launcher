[English](README.md) | [Русский](README.ru.md)

# JL-ComfyUI-Launcher (Enhanced Edition)
Run any ComfyUI workflow with **ZERO setup**. This is an enhanced fork of the original ComfyUI Launcher with significant improvements in stability, error handling, and functionality.

## Key Improvements Over Original Version

### 1. Enhanced Reliability
- Improved error handling during installation
- Better dependency management
- Fixed symbolic links issues
- Automatic retries for downloads
- Download speed monitoring
- Improved file integrity checks

### 2. Project Management
- Automatic creation of batch files for each project
- Enhanced workflow import system
- Better dependency handling
- Improved status monitoring
- Installation progress visualization
- Each project in its own isolated environment

### 3. Model Management
- Automatic model detection and downloading
- Proper model sorting by folders
- Original filenames preservation
- Correct dependency and path setup
- Download progress visualization
- Support for multiple model sources

### 4. Technical Improvements
- Improved Python environment setup
- Better CUDA integration
- Enhanced virtual environment management
- Improved logging system
- Multiple source support for models
- Optimized package installation

## Original Features
- Automatically installs custom nodes, missing model files, etc.
- Workflows exported by this tool can be run by anyone with **ZERO setup**
- Work on multiple ComfyUI workflows at the same time
- Each workflow runs in its own isolated environment
- Prevents workflows from breaking when updating custom nodes, ComfyUI, etc.

## System Requirements

### Windows
- NVIDIA GPU recommended (for CUDA version)
- Windows 10/11
- 8GB RAM minimum
- 20GB free disk space

### Installation Options

#### Portable Version Downloads
Ready-to-use portable versions:
- [CUDA Version](https://jl-comfyui.hhos.net/JL-Portable/ComfyUI-Launcher-Portable-CUDA.7z) (for NVIDIA GPUs)
- DirectML Version (for AMD/Intel GPUs) - Coming soon
- CPU Version - Coming soon

#### Manual Installation
```bash
git clone https://github.com/John-LapTev/JL-ComfyUI-Launcher.git
cd JL-ComfyUI-Launcher/
```

## Usage

### First Launch
1. Run `start.bat` as administrator (only first time)
2. Wait for initial setup to complete
3. Access the interface at http://localhost:4000

### Important Notes
- Run as administrator only for first launch
- Keep antivirus exclusions for the launcher folder
- Close all ComfyUI processes before launching
- Make sure you have enough disk space

## Troubleshooting
If you encounter issues:
1. Close all ComfyUI windows
2. Delete the .celery folder in the server folder if it exists
3. Run start.bat as administrator
4. Check the log files in the launcher folder

## Development
Want to contribute? Great!
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Donations
If you find this fork useful:
- [Support on Boosty](https://boosty.to/jlsd/donate)

Original project:
- [Buy Me A Coffee](https://www.buymeacoffee.com/comfy.workflows)

## Credits
- Original ComfyUI Launcher by ComfyWorkflows
- ComfyUI Manager (https://github.com/ltdrdata/ComfyUI-Manager/)

## License
GNU Affero General Public License v3.0 - see [LICENSE](LICENSE) for details