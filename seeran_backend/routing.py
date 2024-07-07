from django.urls import re_path

from chats import consumers

websocket_urlpatterns = [
    re_path('ws/users', consumers.MainConsumer.as_asgi()),
    # Add more websocket routes as needed
]
