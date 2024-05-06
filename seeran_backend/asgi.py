import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from messages.routing import websocket_urlpatterns


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seeran_backend.settings')

wsgi_application = get_asgi_application()


application = ProtocolTypeRouter(
    {
        "http": wsgi_application,  # Regular Django ASGI application for HTTP
        "websocket": AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)  # WebSocket routing
        ),
    }
)