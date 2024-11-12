from celery import Celery
from kombu import Queue
import os

# Настройка путей для Redis
redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_port = os.environ.get('REDIS_PORT', '6379')

app = Celery('server',
             broker=f'redis://{redis_host}:{redis_port}/0',
             backend=f'redis://{redis_host}:{redis_port}/0')

# Явно регистрируем задачу
app.conf.task_routes = {
    'tasks.create_comfyui_project': {'queue': 'celery'}
}

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Istanbul',
    enable_utc=True,
    task_queues=(Queue('celery'),),
    task_default_queue='celery',
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    broker_connection_timeout=30,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1,
    worker_pool_restarts=True,
    worker_pool='solo',
    task_track_started=True,
    task_time_limit=3600,
    redis_max_connections=20,
    redis_socket_timeout=30,
    redis_socket_connect_timeout=30,
    task_ignore_result=False,  # Важно для отслеживания результатов
    task_always_eager=False    # Важно для асинхронного выполнения
)

# Дополнительные настройки для Windows
if os.name == 'nt':
    app.conf.update(
        broker_transport_options={'visibility_timeout': 3600},
        result_backend_transport_options={'visibility_timeout': 3600}
    )

# Импортируем задачи
import tasks