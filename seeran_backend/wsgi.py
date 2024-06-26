"""
WSGI config for seeran_backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""
from dotenv import load_dotenv

load_dotenv()

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seeran_backend.settings')

application = get_wsgi_application()
