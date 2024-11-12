[English](README_MacOS.md) | [Русский](README_MacOS.ru.md)

# MacOS Build Instructions

## Building from Source

1. Clone the repository:
```bash
git clone https://github.com/John-LapTev/JL-ComfyUI-Launcher.git
cd JL-ComfyUI-Launcher
```

2. Install Python requirements:
```bash
cd builder
pip3 install -r requirements.txt
```

3. Make the build script executable:
```bash
chmod +x scripts/run_as_admin.sh
```

4. Run the builder in either way:
```bash
# From builder directory:
sudo ./scripts/run_as_admin.sh

# Or from scripts directory:
cd scripts
sudo ./run_as_admin.sh
```

5. When prompted, select build type:
- 3 for CPU (MacOS currently only supports CPU version)

6. Wait for the build process to complete
   - A new directory will be created: `../ComfyUI-Launcher-Portable-MACOS`
   - All build logs will be saved in the builder directory

## Build Output

The build process will create a portable directory in the same folder where the build script is located:
```
builder/
├── build_portable.py
├── run_as_admin.sh
└── ComfyUI-Launcher-Portable-MACOS/  # Created here
```

Alternatively, you can copy build_portable.py and run_as_admin.sh to any convenient location:
```
Your-Chosen-Directory/
├── build_portable.py
├── run_as_admin.sh
└── ComfyUI-Launcher-Portable-MACOS/  # Will be created here
```

## Using Pre-built Version

If you don't want to build from source, you can download the pre-built version:
1. [MacOS Version](https://jl-comfyui.hhos.net/JL-Portable/ComfyUI-Launcher-Portable-MACOS.7z)

## Important Notes for MacOS

1. Unlike Windows, on MacOS you can't just double-click scripts
2. Every launch must be done through Terminal
3. Commands must be typed exactly, including the `./` before script names
4. When entering password, no characters will be displayed - this is normal

## Common Issues

1. "Permission denied":
   - Make sure you ran chmod +x
   - Verify you're in correct directory

2. "Command not found":
   - Verify you're in correct directory
   - Check script name is typed correctly

3. Terminal issues:
   - Enter commands without quotes
   - Case sensitive (uppercase/lowercase matters)

## System Requirements
- MacOS 11 or newer
- Python 3.10+
- Terminal (built into MacOS)
- Administrator rights
- 16GB RAM recommended
- 40GB free disk space
- Internet connection