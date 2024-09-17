# python
from __future__ import absolute_import, unicode_literals
import os
from decouple import config
import ssl

# celery
from celery import Celery


# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seeran_backend.settings')

app = Celery('seeran_backend')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Update the configuration
app.conf.update(
    broker_url='rediss://' + config('CACHE_LOCATION') + ':6378',
    result_backend=None,  # Do not store task results
    broker_transport_options={
        'ssl_cert_reqs': ssl.CERT_REQUIRED,  # Ensure SSL certificate is required
        'ssl_ca_certs': config('SERVER_CA_CERT'),  # Path to CA certificates
    },
)