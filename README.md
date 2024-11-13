[English](README.md) | [Русский](README.ru.md)

# JL-ComfyUI-Launcher (Enhanced Edition)

Run any ComfyUI workflow with **ZERO setup**. This is an enhanced fork of the original ComfyUI Launcher with significant improvements in stability, error handling, and functionality.

## Community
Join our community:
- [Telegram Group](https://t.me/JL_Stable_Diffusion) - News, updates, and discussions about AI
- [Boosty Blog](https://boosty.to/jlsd) - Builds, tutorials, and more

## Quick Install

You don't need to clone the entire repository to create a portable version. Just download two files:

### Windows
1. Download:
   - [build_portable.py](https://raw.githubusercontent.com/John-LapTev/JL-ComfyUI-Launcher/main/builder/build_portable.py)
   - [run_as_admin.bat](https://raw.githubusercontent.com/John-LapTev/JL-ComfyUI-Launcher/main/builder/scripts/run_as_admin.bat)
2. Place both files in the same directory
3. Run `run_as_admin.bat`

### MacOS
1. Download:
   - [build_portable.py](https://raw.githubusercontent.com/John-LapTev/JL-ComfyUI-Launcher/main/builder/build_portable.py)
   - [run_as_admin.sh](https://raw.githubusercontent.com/John-LapTev/JL-ComfyUI-Launcher/main/builder/scripts/run_as_admin.sh)
2. Place both files in the same directory
3. Make the script executable: `chmod +x run_as_admin.sh`
4. Run: `sudo ./run_as_admin.sh`

## Key Improvements

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

## Getting Started

### Option 1: Download Ready-to-Use Version
Download and unpack pre-built version:
- [CUDA Version](https://jl-comfyui.hhos.net/JL-Portable/ComfyUI-Launcher-Portable-CUDA.7z) (for NVIDIA GPUs)
- DirectML Version (for AMD/Intel GPUs) - Coming soon
- CPU Version - Coming soon
- MacOS Version - Coming soon

### Option 2: Build from Source
```bash
git clone https://github.com/John-LapTev/JL-ComfyUI-Launcher.git
cd JL-ComfyUI-Launcher/builder
```
For detailed build instructions, see:
- [Windows Build Guide](builder/README_Windows.md)
- [MacOS Build Guide](builder/README_MacOS.md)

## System Requirements

### Windows
- Windows 10 or 11
- NVIDIA GPU recommended (for CUDA version)
- AMD or Intel GPU (for DirectML version)
- 8GB RAM minimum (16GB recommended)
- 20GB free disk space

### MacOS
- MacOS 11 or newer
- 8GB RAM minimum (16GB recommended)
- 20GB free disk space

## First Launch
1. Run `start.bat` (Windows) or `start.sh` (MacOS)
2. Wait for initial setup to complete
3. Access the interface at http://localhost:4000

## Important Notes
- Add launcher folder to antivirus exclusions
- Close all ComfyUI processes before launching
- Make sure you have enough disk space
- Recommended to install in a directory with a short path (e.g., `C:\ComfyUI` instead of `C:\Users\Username\Documents\Projects\ComfyUI`)

## Troubleshooting

### Common Issues
1. Close all ComfyUI windows
2. Delete the .celery folder in the server folder if it exists
3. Restart start.bat/start.sh
4. Check the log files in the launcher folder

### Long Path Issues in Windows
If you encounter errors related to long paths during installation or workflow import:

1. Enable long path support in Windows:
   - Open Group Policy Editor (gpedit.msc)
   - Navigate to: Computer Configuration → Administrative Templates → System → Filesystem
   - Find "Enable Win32 long paths"
   - Set it to "Enabled"
   - Restart your computer

2. Or use a short installation path:
   - Install the launcher closer to the root directory
   - Example: `C:\ComfyUI` instead of `C:\Users\Username\Documents\Projects\ComfyUI`

## Development
Want to contribute? Great!
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Support the Project
If you find this project useful:
- [Support on Boosty](https://boosty.to/jlsd/donate)

## Credits
- Original ComfyUI Launcher by ComfyWorkflows
- ComfyUI Manager (https://github.com/ltdrdata/ComfyUI-Manager/)

## License
GNU Affero General Public License v3.0 - see [LICENSE](LICENSE) for details