import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from messages.routing import websocket_urlpatterns
from channels.layers import get_channel_layer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seeran_backend.settings')

wsgi_application = get_asgi_application()
channel_layer = get_channel_layer()

application = ProtocolTypeRouter(
    {
        "http": wsgi_application,  # Regular Django ASGI application for HTTP
        "websocket": AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)  # WebSocket routing
        ),
    }
)