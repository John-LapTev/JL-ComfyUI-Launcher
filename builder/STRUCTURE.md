[English](STRUCTURE.md) | [Русский](STRUCTURE.ru.md)

# Builder Directory Structure

```
builder/
├── build_portable.py     # Main build script for portable version
├── requirements.txt      # Python dependencies for builder
├── README.md            # General build instructions (English)
├── README.ru.md         # General build instructions (Russian)
├── README_MacOS.md      # MacOS specific instructions (English)
├── README_MacOS.ru.md   # MacOS specific instructions (Russian)
├── README_Windows.md    # Windows specific instructions (English)
├── README_Windows.ru.md # Windows specific instructions (Russian)
├── STRUCTURE.md         # This file - describes directory structure
├── STRUCTURE.ru.md      # Structure description in Russian
└── scripts/             # Helper scripts directory
    ├── run_as_admin.bat # Windows build launcher
    └── run_as_admin.sh  # MacOS/Linux build launcher
```

## File Descriptions

### Main Files
- `build_portable.py` - Main script that creates portable version of JL-ComfyUI-Launcher
- `requirements.txt` - List of Python packages required for build process

### Documentation (All files have English and Russian versions)
- `README.md` - Main documentation and instructions
- `README_MacOS.md` - MacOS specific setup and build instructions
- `README_Windows.md` - Windows specific setup and build instructions
- `STRUCTURE.md` - Documentation of the builder directory structure

### Scripts
- `scripts/run_as_admin.bat` - Windows script to launch builder with admin rights
- `scripts/run_as_admin.sh` - Unix script to launch builder with admin rights

## Build Process
The builder can be launched either from:
1. The scripts/ directory
2. The builder/ directory

The scripts will automatically locate build_portable.py and execute it with proper permissions.