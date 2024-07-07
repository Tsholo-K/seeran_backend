from django.urls import re_path

from chats import consumers

websocket_urlpatterns = [
    re_path('ws/', consumers.ChatConsumer.as_asgi()),
    # Add more websocket routes as needed
]
