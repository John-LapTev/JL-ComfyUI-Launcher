[English](README_Windows.md) | [Русский](README_Windows.ru.md)

# Windows Build Instructions

## Building from Source

1. Clone the repository:
```bash
git clone https://github.com/John-LapTev/JL-ComfyUI-Launcher.git
cd JL-ComfyUI-Launcher
```

2. Install Python requirements:
```bash
cd builder
pip install -r requirements.txt
```

3. Run the builder in either way:
```bash
# From builder directory:
scripts/run_as_admin.bat

# Or from scripts directory:
cd scripts
run_as_admin.bat
```

4. When prompted, select build type:
- 1 for CUDA (NVIDIA GPUs)
- 2 for DirectML (AMD/Intel GPUs)
- 3 for CPU (no GPU required)

5. Wait for the build process to complete
   - A new directory will be created: `../ComfyUI-Launcher-Portable-{TYPE}`
   - All build logs will be saved in the builder directory

## Build Output

The build process will create a portable directory one level up from the repository:
```
Parent Directory/
├── JL-ComfyUI-Launcher/        # Source repository
│   └── builder/                # Builder directory
└── ComfyUI-Launcher-Portable-{TYPE}/  # Built portable version
```

## Using Pre-built Version

If you don't want to build from source, you can download pre-built versions:
1. [CUDA Version](https://jl-comfyui.hhos.net/JL-Portable/ComfyUI-Launcher-Portable-CUDA.7z)
2. DirectML Version (Coming soon)
3. CPU Version (Coming soon)

## Important Notes

- Run builder scripts as administrator
- Make sure you have enough disk space (40GB recommended)
- Close all Python/ComfyUI processes before building
- Check antivirus exclusions if having issues

## System Requirements

- Windows 10 or 11
- Python 3.10 or newer
- Git
- Administrator rights
- 16GB RAM recommended
- 40GB free disk space
- Internet connection

## Troubleshooting

1. "Permission denied":
   - Make sure to run as administrator
   - Check folder permissions

2. "Git is not recognized":
   - Install Git
   - Add Git to PATH

3. Python issues:
   - Make sure Python 3.10+ is installed
   - Check PATH variable
   - Try using python -m pip

4. Antivirus blocking:
   - Add build folder to exceptions
   - Temporarily disable antivirus