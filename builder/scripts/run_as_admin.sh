#!/bin/bash

# Проверяем права администратора
if [ "$EUID" -ne 0 ]; then 
    echo "This script requires administrator rights."
    echo "Please run with sudo:"
    echo "sudo $0"
    exit 1
fi

# Определяем путь к скрипту сборки
if [ -f "build_portable.py" ]; then
    BUILDER_PATH="build_portable.py"
elif [ -f "../build_portable.py" ]; then
    BUILDER_PATH="../build_portable.py"
else
    echo "Error: build_portable.py not found!"
    echo "Please make sure you're in the correct directory"
    read -p "Press Enter to exit..."
    exit 1
fi

# Запускаем build_portable.py
python3 "$BUILDER_PATH"

# Ждем нажатия клавиши
read -p "Press Enter to exit..."