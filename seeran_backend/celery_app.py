# python
from __future__ import absolute_import, unicode_literals
import os

# celery
from celery import Celery


# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seeran_backend.settings')

app = Celery('seeran_backend')

app.conf.update(
    # Other configuration settings
    worker_log_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    worker_task_log_format='%(asctime)s - %(name)s - %(levelname)s - %(task_name)s[%(task_id)s]: %(message)s',
    worker_log_color=False,  # Disable colors if you are writing to a log file
    worker_redirect_stdouts_level='DEBUG',  # Set logging level to DEBUG
)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

