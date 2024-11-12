[English](README.md) | [Русский](README.ru.md)

# JL-ComfyUI-Launcher Builder

This directory contains everything needed to create portable versions of JL-ComfyUI-Launcher.

## Available Build Types

1. CUDA Version (for NVIDIA GPUs)
2. DirectML Version (for AMD/Intel GPUs)
3. CPU Version (no GPU required)
4. MacOS Version

## Quick Start

### Windows
1. Make sure Python 3.10+ is installed
2. Run `scripts/run_as_admin.bat` as administrator
3. Select build type when prompted
4. Wait for build process to complete

### MacOS/Linux
1. Make sure Python 3.10+ is installed
2. Open terminal in this directory
3. Make script executable: `chmod +x scripts/run_as_admin.sh`
4. Run: `sudo ./scripts/run_as_admin.sh`
5. Select build type when prompted
6. Wait for build process to complete

## System Requirements

### Common
- Python 3.10 or newer
- Git
- Administrator rights
- 16GB RAM recommended
- 40GB free disk space
- Internet connection

### Windows
- Windows 10 or 11
- CUDA Toolkit for NVIDIA version (optional)

### MacOS
- MacOS 11 or newer
- Command Line Tools

## Detailed Instructions

- [Windows Instructions](README_Windows.md)
- [MacOS Instructions](README_MacOS.md)

## Build Structure

See [STRUCTURE.md](STRUCTURE.md) for detailed description of directories and files.

## Build Process

1. Downloads required components:
   - Python 3.10.6
   - Redis Server
   - Node.js
   - CUDA DLLs (for CUDA version)

2. Creates directory structure:
   - python/
   - redis/
   - nodejs/
   - launcher/
   - models/
   - cuda/ (CUDA version only)

3. Sets up virtual environments and installs dependencies

4. Creates startup scripts

Full process documentation in [STRUCTURE.md](STRUCTURE.md)

## Output

After successful build, you'll get:
```
ComfyUI-Launcher-Portable-{TYPE}/
├── python/
├── redis/
├── nodejs/
├── launcher/
├── models/
├── cuda/ (CUDA version only)
├── start.bat (Windows)
└── start.sh (MacOS/Linux)
```

## Troubleshooting

If build fails:
1. Check log files in the builder directory
2. Make sure all requirements are installed
3. Try running as administrator
4. Check available disk space
5. Verify internet connection

For specific platform issues, see:
- [Windows Instructions](README_Windows.md)
- [MacOS Instructions](README_MacOS.md)