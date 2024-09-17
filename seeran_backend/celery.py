# python
from __future__ import absolute_import, unicode_literals
import os

# celery initialization
from .celery_initialization import app


# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seeran_backend.settings')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

