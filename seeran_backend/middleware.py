from channels.db import database_sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.core.cache import cache
from users.models import CustomUser
from rest_framework_simplejwt.tokens import AccessToken
from authentication.utils import validate_access_token, refresh_access_token

class TokenAuthMiddleware:
    def __init__(self, app):
        self.app = app

    @database_sync_to_async
    def get_user(self, user_id):
        return CustomUser.objects.get(pk=user_id)

    async def __call__(self, scope, receive, send):

        headers = dict(scope['headers'])
        if b'cookie' in headers:

            cookies = headers[b'cookie'].decode()
            access_token = cookies.get('access_token')
            refresh_token = cookies.get('refresh_token')

            if not refresh_token or cache.get(refresh_token):
                await send({
                    'type': 'websocket.close',
                    'code': 1000,
                    'text': 'Request not authenticated.. access denied'
                })
                return

            if not access_token:
                new_access_token = refresh_access_token(refresh_token)
                
            else:
                new_access_token = validate_access_token(access_token)
                if new_access_token is None:
                    new_access_token = refresh_access_token(refresh_token)

            if new_access_token:
                decoded_token = AccessToken(new_access_token)
                try:
                    scope['user'] = await self.get_user(decoded_token['user_id'])
                except ObjectDoesNotExist:
                    await send({
                        'type': 'websocket.close',
                        'code': 1000,
                        'text': 'Invalid credentials.. no such user exists'
                    })
                    return
            else:
                await send({
                    'type': 'websocket.close',
                    'code': 1000,
                    'text': 'Invalid security credentials.. request revoked'
                })
                return

        return await self.app(scope, receive, send)