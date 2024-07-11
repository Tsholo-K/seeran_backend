# python
import json

# channels
from channels.generic.websocket import AsyncWebsocketConsumer

# utility functions
from authentication.utils import validate_access_token

# async functions 
from users.consumers import general_async_functions
from users.consumers.admin import admin_async_functions

class AdminConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Get the user's role from the scope
        role = self.scope.get('role')

        # Check if the user has the required role
        if role not in ['ADMIN', 'PRINCIPAL']:
            return await self.close()
        
        await self.accept()
        return await self.send(text_data=json.dumps({ 'message': 'Welcome' }))


    async def disconnect(self, close_code):
        pass


    async def receive(self, text_data):
        
        user = self.scope.get('user')
        access_token = self.scope.get('access_token')
        
        if user and access_token and (validate_access_token(access_token) is not None):
            
            response = None

            action = json.loads(text_data).get('action')
            description = json.loads(text_data).get('description')
            
            if not ( action or description ):
                return await self.send(text_data=json.dumps({ 'error': 'invalid request..' }))


            ################################################ GET #######################################################


            if action == 'GET':
                
                # return users security information
                if description == 'my_security_information':
                    response = await general_async_functions.fetch_security_info(user)
                    
                # return user email information
                if description == 'my_email_information':
                    response = await general_async_functions.fetch_email_information(user)
                    
                # log user out of the system
                if description == 'log_me_out':
                    response = await general_async_functions.log_user_out(access_token)


            ##############################################################################################################


                if response is not None:
                    return await self.send(text_data=json.dumps(response))
                
                return await self.send(text_data=json.dumps({ 'error': 'provided information is invalid.. request revoked' }))
            
            details = json.loads(text_data).get('details')
            
            if not details:
                return await self.send(text_data=json.dumps({ 'error': 'invalid request.. request denied' }))


            ############################################## SEARCH ########################################################


            if action == 'SEARCH':
                
                # return email ban with the provided id
                if description == 'my_email_ban':
                    email_ban_id = details.get('email_ban_id')
                    email = details.get('email')
                    if (email_ban_id and email) is not None:
                        response = await general_async_functions.search_email_ban(email, email_ban_id)
                        
                # return school accounts with the provided role
                if description == 'my_school_accounts':
                    role = details.get('role')
                    if role is not None:
                        response = await admin_async_functions.search_my_school_accounts(user, role)
                        
                # return school account with the provided id
                if description == 'my_school_account':
                    account_id = details.get('account_id')
                    if account_id is not None:
                        response = await admin_async_functions.search_my_school_account(user, account_id)

            ##############################################################################################################

            ############################################## VERIFY ########################################################


            if action == 'VERIFY':
                        
                # verify email before email update
                if description == 'verify_email':
                    email = details.get('email')
                    if email is not None:
                        status = await general_async_functions.verify_email(email)
                        if status.get('user'):
                            response = await general_async_functions.send_one_time_pin_email(status.get('user'), reason='This OTP was generated in response to your email update request..')
                        else:
                            response = status
                
                # verify password before password update
                if description == 'verify_password':
                    password = details.get('password')
                    if password is not None:
                        status = await general_async_functions.verify_password(user, password)
                        if status.get('user'):
                            response = await general_async_functions.send_one_time_pin_email(status.get('user'), reason='This OTP was generated in response to your password update request..')
                        else:
                            response = status
                
                # verify otp
                if description == 'verify_otp':
                    otp = details.get('otp')
                    if otp is not None:
                        response = await general_async_functions.verify_otp(user, otp)
                
                # verify email revalidation otp
                if description == 'verify_email_revalidation_otp':
                    otp = details.get('otp')
                    email_ban_id = details.get('email_ban_id')
                    if (otp and email_ban_id) is not None:
                        response = await general_async_functions.verify_email_revalidate_otp(user, otp, email_ban_id)


            ################################################################################################################                
                        
            ################################################ PUT ##########################################################


            if action == 'PUT':
                
                # update users email
                if description == 'update_email':
                    new_email = details.get('new_email')
                    authorization_otp = details.get('authorization_otp')
                    if (new_email and authorization_otp) is not None:
                        response = await general_async_functions.update_email(user, new_email, authorization_otp, access_token)
                
                # update users password
                if description == 'update_password':
                    new_password = details.get('new_password')
                    authorization_otp = details.get('authorization_otp')
                    if (new_password and authorization_otp) is not None:
                        response = await general_async_functions.update_password(user, new_password, authorization_otp, access_token)

                # toggle  multi-factor authentication option for user
                if description == 'update_multi_factor_authentication':
                    toggle = details.get('toggle')
                    if toggle is not None:
                        response = await general_async_functions.update_multi_factor_authentication(user, toggle)
                        
                # send email revalidation otp
                if description == 'send_email_revalidation_otp':
                    email_ban_id = details.get('email_ban_id')
                    if email_ban_id is not None:
                        status = await general_async_functions.validate_email_revalidation(user, email_ban_id)
                        if status.get('user'):
                            status = await general_async_functions.send_email_revalidation_one_time_pin_email(status.get('user'))
                            if status.get('message'):
                                response = await general_async_functions.update_email_ban(email_ban_id)
                            else:
                                response = status
                        else:
                            response = status


            ################################################################################################################                
                        
            ################################################# POST ##########################################################


            if action == 'POST':
                
                # create account with role in [ADMIN, TEACHER]
                if description == 'create_account':
                    status = await admin_async_functions.create_account(user, details)
                    if status.get('user'):
                        response = await general_async_functions.send_account_confirmation_email(status.get('user'))
                    else:
                        response = status
                

            ###############################################################################################################
        
                        
            if response is not None:
                return await self.send(text_data=json.dumps(response))
            
            return await self.send(text_data=json.dumps({ 'error': 'provided information is invalid.. request revoked' }))
        
        return await self.send(text_data=json.dumps({ 'error': 'request not authenticated.. access denied' }))
