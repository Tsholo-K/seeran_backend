"""
    The asgi.py file is the entry point for your ASGI server. 
    It uses a ProtocolTypeRouter to inspect the type of connection coming in:
    For HTTP requests, it uses Django's ASGI application (get_asgi_application()), 
    which in turn uses your URL configuration (urls.py file) to route the request
    to the appropriate view based on the URL path.
    For WebSocket connections, it uses the application object from your routing.py file. 
    This object is another ProtocolTypeRouter that routes the WebSocket connection to the 
    appropriate consumer based on the WebSocket path.
    So, in summary, the asgi.py file routes HTTP requests and WebSocket connections to different 
    places based on their type, and then the URL configuration (urls.py file) and the routing.py file 
    further route those requests/connections based on their path.
"""
import django
django.setup()

import os

# django
from django.core.asgi import get_asgi_application
from django.urls import path

# channels
from channels.routing import ProtocolTypeRouter, URLRouter

# consumers
from websockets.consumers.authentication.authentication_consumer import WebsocketHandler


# middleware
from .middleware import TokenAuthMiddleware


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seeran_backend.settings')


application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": TokenAuthMiddleware(
        URLRouter([
            path('ws/accounts/', WebsocketHandler.as_asgi()),
        ])
    ),
})