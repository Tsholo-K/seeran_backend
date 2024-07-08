from channels.db import database_sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.core.cache import cache
from users.models import CustomUser
from rest_framework_simplejwt.tokens import AccessToken
from authentication.utils import validate_access_token

class TokenAuthMiddleware:
    def __init__(self, app):
        self.app = app

    @database_sync_to_async
    def get_user(self, user_id):
        return CustomUser.objects.get(pk=user_id)

    async def __call__(self, scope, receive, send):

        headers = dict(scope['headers'])
        if b'cookie' in headers:
            
            try:
                cookies = headers[b'cookie'].decode()
                
                cookie_dict = {}
                for cookie in cookies.split('; '):
                    cookie_parts = cookie.split('=')
                    cookie_dict[cookie_parts[0]] = cookie_parts[1] if len(cookie_parts) > 1 else ''

                access_token = cookie_dict.get('access_token')

                if not access_token or cache.get(access_token):
                    await send({ 'type': 'websocket.close', 'code': 1000, 'text': 'Request not authenticated.. access denied' })
                    return

                authorized = validate_access_token(access_token)
                
                if authorized is None:
                    await send({ 'type': 'websocket.close', 'code': 1000, 'text': 'Invalid security credentials.. request revoked' })
                    return

                decoded_token = AccessToken(access_token)
                
                scope['user'] = await self.get_user(decoded_token['user_id'])
                
            except ObjectDoesNotExist:
                await send({ 'type': 'websocket.close', 'code': 1000, 'text': 'Invalid credentials.. no such user exists' })
                return
            
            # if any exception occurs during the proccess return an error
            except Exception as e:
                await send({ 'type': 'websocket.close', 'code': 1000, 'text': str(e) })
                return

        return await self.app(scope, receive, send)