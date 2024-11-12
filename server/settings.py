import os
from celery.backends.redis import RedisBackend

# Создание необходимых директорий
os.makedirs(os.environ.get("PROJECTS_DIR", "./projects"), exist_ok=True)
PROJECTS_DIR = os.environ.get("PROJECTS_DIR", "./projects")

os.makedirs(os.environ.get("MODELS_DIR", "./models"), exist_ok=True)
MODELS_DIR = os.environ.get("MODELS_DIR", "./models")

os.makedirs(os.environ.get("TEMPLATES_DIR", "./templates"), exist_ok=True)
TEMPLATES_DIR = os.environ.get("TEMPLATES_DIR", "./templates")

os.makedirs(os.environ.get("CELERY_DIR", ".celery"), exist_ok=True)
os.makedirs(os.path.join(os.environ.get("CELERY_DIR", ".celery"), "results"), exist_ok=True)
os.makedirs(os.path.join(os.environ.get("CELERY_DIR", ".celery"), "broker"), exist_ok=True)

CELERY_RESULTS_DIR = os.path.join(os.environ.get("CELERY_DIR", ".celery"), "results")
CELERY_BROKER_DIR = os.path.join(os.environ.get("CELERY_DIR", ".celery"), "broker")

# Redis configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_TASK_ALWAYS_EAGER = False  # Изменено с True на False
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Добавленные настройки Redis
BROKER_CONNECTION_RETRY = True
BROKER_CONNECTION_RETRY_ON_STARTUP = True
BROKER_CONNECTION_MAX_RETRIES = 10
BROKER_CONNECTION_TIMEOUT = 30
REDIS_MAX_CONNECTIONS = 20
REDIS_SOCKET_TIMEOUT = 30
REDIS_SOCKET_CONNECT_TIMEOUT = 30

# Proxy and port settings
PROXY_MODE = os.environ.get("PROXY_MODE", "false").lower() == "true"
ALLOW_OVERRIDABLE_PORTS_PER_PROJECT = os.environ.get("ALLOW_OVERRIDABLE_PORTS_PER_PROJECT", "true").lower() == "true"
PROJECT_MIN_PORT = int(os.environ.get("PROJECT_MIN_PORT", "4001"))
PROJECT_MAX_PORT = int(os.environ.get("PROJECT_MAX_PORT", "4100"))
SERVER_PORT = int(os.environ.get("SERVER_PORT", "4000"))

# Additional settings for Windows
CELERY_POOL_RESTARTS = True
CELERY_WORKER_POOL = 'solo'
CELERYD_POOL_RESTARTS = True