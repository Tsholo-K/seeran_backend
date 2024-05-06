# chat/consumers.py

from channels.generic.websocket import AsyncWebsocketConsumer
import json

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Called when the WebSocket connection is established
        await self.accept()

    async def disconnect(self, close_code):
        # Called when the WebSocket connection is closed
        pass

    async def receive(self, text_data):
        # Called when a message is received from the WebSocket
        data = json.loads(text_data)
        message = data.get('message')

        # Send the received message back to the client
        await self.send(text_data=json.dumps({'message': message}))
