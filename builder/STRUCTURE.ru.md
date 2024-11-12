[English](STRUCTURE.md) | [Русский](STRUCTURE.ru.md)

# Структура Директории Builder

```
builder/
├── build_portable.py     # Основной скрипт создания портативной версии
├── requirements.txt      # Python зависимости для сборщика
├── README.md            # Общие инструкции по сборке (английский)
├── README.ru.md         # Общие инструкции по сборке (русский)
├── README_MacOS.md      # Инструкции для MacOS (английский)
├── README_MacOS.ru.md   # Инструкции для MacOS (русский)
├── README_Windows.md    # Инструкции для Windows (английский)
├── README_Windows.ru.md # Инструкции для Windows (русский)
├── STRUCTURE.md         # Этот файл - описание структуры (английский)
├── STRUCTURE.ru.md      # Описание структуры (русский)
└── scripts/             # Директория вспомогательных скриптов
    ├── run_as_admin.bat # Скрипт запуска для Windows
    └── run_as_admin.sh  # Скрипт запуска для MacOS/Linux
```

## Описание Файлов

### Основные Файлы
- `build_portable.py` - Основной скрипт, создающий портативную версию JL-ComfyUI-Launcher
- `requirements.txt` - Список Python пакетов, необходимых для сборки

### Документация (Все файлы имеют английскую и русскую версии)
- `README.md` - Основная документация и инструкции
- `README_MacOS.md` - Специфичные инструкции для MacOS
- `README_Windows.md` - Специфичные инструкции для Windows
- `STRUCTURE.md` - Документация по структуре директории builder

### Скрипты
- `scripts/run_as_admin.bat` - Windows скрипт для запуска сборщика с правами администратора
- `scripts/run_as_admin.sh` - Unix скрипт для запуска сборщика с правами администратора

## Процесс Сборки
Сборщик может быть запущен из:
1. Директории scripts/
2. Директории builder/

Скрипты автоматически найдут build_portable.py и запустят его с необходимыми правами.