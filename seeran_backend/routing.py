from channels.routing import ProtocolTypeRouter, URLRouter

from django.urls import path

from chats import consumers

application = ProtocolTypeRouter({
    'websocket': URLRouter([
        path('ws/', consumers.ChatConsumer.as_asgi()),
    ]),
})
