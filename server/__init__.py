from flask import Flask
from celery import Celery
import os

app = Flask(__name__)

# Настройка Redis
redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_port = os.environ.get('REDIS_PORT', '6379')

app.config.from_mapping(
    CELERY=dict(
        broker_url=f'redis://{redis_host}:{redis_port}/0',
        result_backend=f'redis://{redis_host}:{redis_port}/0',
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        broker_connection_retry=True,
        broker_connection_retry_on_startup=True,
        broker_connection_max_retries=10,
        broker_connection_timeout=30,
        redis_max_connections=20,
        redis_socket_timeout=30,
        redis_socket_connect_timeout=30,
        task_ignore_result=False,
        task_always_eager=False
    ),
)

celery = Celery(app.name)
celery.conf.update(app.config["CELERY"])

# Импортируем задачи
import tasks