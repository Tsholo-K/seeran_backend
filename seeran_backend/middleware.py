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
        user =  CustomUser.objects.get(pk=user_id)
        return ( user.account_id, user.role )

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
                    return await send({ 'type': 'websocket.close', 'code': 1000, 'error': 'Request not authenticated.. access denied' })

                authorized = validate_access_token(access_token)
                
                if authorized is None:
                    return await send({ 'type': 'websocket.close', 'code': 1000, 'error': 'Invalid security credentials.. request revoked' })

                decoded_token = AccessToken(access_token)
                
                scope['user'], scope['role'] = await self.get_user(decoded_token['user_id'])
                scope['access_token'] = access_token
                
            except ObjectDoesNotExist:
                return await send({ 'type': 'websocket.close', 'code': 1000, 'error': 'Invalid credentials.. no such user exists' })
            
            # if any exception occurs during the proccess return an error
            except Exception as e:
                return await send({ 'type': 'websocket.close', 'code': 1000, 'error': str(e) })

        return await self.app(scope, receive, send)