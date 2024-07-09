# python 
from decouple import config
import requests
import base64

from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async

# django
from django.db.models import Count, Q
from django.db import models
from django.db import transaction

# httpx
import httpx

# models 
from balances.models import Bill
from users.models import CustomUser
from users.models import CustomUser
from schools.models import School
from balances.models import Balance
from bug_reports.models import BugReport

# serializers
from balances.serializers import BillsSerializer, BillSerializer
from schools.serializers import SchoolCreationSerializer, SchoolsSerializer, SchoolSerializer, SchoolDetailsSerializer
from users.serializers import ProfileSerializer, PrincipalCreationSerializer
from bug_reports.serializers import CreateBugReportSerializer, BugReportsSerializer, UnresolvedBugReportSerializer, ResolvedBugReportSerializer, UpdateBugReportStatusSerializer, MyBugReportSerializer


class FounderConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Get the user's role from the scope
        role = self.scope.get('role')

        # Check if the user has the required role
        if role != 'FOUNDER':
            # Optionally, send a message to the client before closing the connection
            await self.send(text_data=json.dumps({ 'error': 'insufficient permissions' }))
            return await self.close()
        
        await self.accept()
        return await self.send(text_data=json.dumps({ 'message': 'WebSocket connection established' }))


    async def disconnect(self, close_code):
        pass


    async def receive(self, text_data):
        
        user = self.scope.get('user')
        
        if user:
            response = None
            
            action = json.loads(text_data).get('action')
            description = json.loads(text_data).get('description')
            
            if not ( action or description ):
                return await self.send(text_data=json.dumps({ 'error': 'invalid request.. permission denied' }))


            ################################################ GET #######################################################


            if action == 'GET':
                
                # return users security information
                if description == 'my_security_information':
                    response = await self.fetch_security_info(user)
                
                # return all school objects
                if description == 'schools':
                    response = await self.fetch_schools()


            ##############################################################################################################


                if response is not None:
                    return await self.send(text_data=json.dumps(response))
                return await self.send(text_data=json.dumps({ 'error': 'provided information is invalid.. request revoked' }))
            
            details = json.loads(text_data).get('details')
            
            if not details:
                return await self.send(text_data=json.dumps({ 'error': 'invalid request.. permission denied' }))


            ############################################## SEARCH ########################################################


            if action == 'SEARCH':
                
                # return school with the provided id
                if description == 'school':
                    school_id = details.get('school_id')
                    if school_id is not None:
                        response = await self.search_school(school_id)
                        
                # return school details for school with the provided id
                if description == 'school_details':
                    school_id = details.get('school_id')
                    if school_id is not None:
                        response = await self.search_school_details(school_id)
                        
                # return profile for principal with the provided id
                if description == 'principal_profile':
                    principal_id = details.get('principal_id')
                    if principal_id is not None:
                        response = await self.search_principal_profile(principal_id)
                        
                # return all principal invoices
                if description == 'principal_invoices':
                    principal_id = details.get('principal_id')
                    if principal_id is not None:
                        response = await self.search_principal_invoices(principal_id)
                        
                # return principal invoice with provided id
                if description == 'principal_invoice':
                    invoice_id = details.get('invoice_id')
                    if invoice_id is not None:
                        response = await self.search_principal_invoice(invoice_id)
                        
                # return bug reports
                if description == 'bug_reports':
                    resolved = details.get('resolved')
                    if resolved is not None:
                        response = await self.search_bug_reports(resolved)
                                        
                # return bug report with provided id
                if description == 'bug_report':
                    bug_report_id = details.get('bug_report_id')
                    if bug_report_id is not None:
                        response = await self.search_bug_report(bug_report_id)


            ##############################################################################################################

            ################################################ PUT ##########################################################


            if action == 'PUT':
                
                # toggle  multi-factor authentication option for user
                if description == 'multi_factor_authentication':
                    toggle = details.get('toggle')
                    if toggle is not None:
                        response = await self.update_multi_factor_authentication(user, toggle)


            ################################################################################################################                
                        
            ################################################# POST ##########################################################


            if action == 'POST':
                
                # create school account
                if description == 'create_school_account':
                    response = await self.create_school_account(details)
                
                # delete school account
                if description == 'delete_school_account':
                    school_id = details.get('school_id')
                    if school_id is not None:
                        response = await self.delete_school_account(school_id)
                        
                # create school account
                if description == 'create_principal_account':
                    school_id = details.get('school')
                    if school_id is not None:
                        status = await self.create_principal_account(details, school_id)
                        if status.get('message'):
                            response = await self.send_email(status.get('user'))
                        else:
                            response = status.get('error')
                    
                # delete principal account
                if description == 'delete_principal_account':
                    principal_id = details.get('principal_id')
                    if principal_id is not None:
                        response = await self.delete_principal_account(principal_id)


            ###############################################################################################################
        
                        
            if response is not None:
                return await self.send(text_data=json.dumps(response))
            return await self.send(text_data=json.dumps({ 'error': 'provided information is invalid.. request revoked' }))
        
        return await self.send(text_data=json.dumps({ 'error': 'request not authenticated.. access denied' }))


########################################################## Aysnc Functions ########################################################



    @database_sync_to_async
    def fetch_security_info(self, user):

        try:
            user = CustomUser.objects.get(account_id=user)
            return { 'multifactor_authentication': user.multifactor_authentication, 'event_emails': user.event_emails }
            
        except CustomUser.DoesNotExist:
            return { 'error': 'user with the provided credentials does not exist' }
        
        except Exception as e:
            return { 'error': str(e) }


    @database_sync_to_async
    def update_multi_factor_authentication(self, user, toggle):
        # Example: Fetch security information asynchronously from CustomUser model
        try:
            user = CustomUser.objects.get(account_id=user)
            user.multifactor_authentication = toggle
            user.save()
            
            return {'message': 'Multifactor authentication {} successfully'.format('enabled' if toggle else 'disabled')}
        
        except CustomUser.DoesNotExist:
            return { 'error': 'user with the provided credentials does not exist' }
        
        except Exception as e:
            return { 'error': str(e) }
        
        
    @database_sync_to_async
    def search_principal_profile(self, principal_id):

        try:
            principal = CustomUser.objects.get(account_id=principal_id, role='PRINCIPAL')
            
            serializer = ProfileSerializer(instance=principal)
            return { "user" : serializer.data }
        
        except CustomUser.DoesNotExist:
            return { 'error': 'principal with the provided credentials does not exist' }
        
        except Exception as e:
            return { 'error': str(e) }


    @database_sync_to_async
    def search_principal_invoices(self, principal_id):

        try:
            # Get the principal instance
            principal = CustomUser.objects.get(account_id=principal_id)
            
            # Get the principal's bills
            principal_bills = Bill.objects.filter(user=principal).order_by('-date_billed')
            
            if not principal_bills:
                return { 'message' : 'success', "invoices" : None, 'in_arrears': principal.school.in_arrears}
            
            # Serialize the bills
            serializer = BillsSerializer(principal_bills, many=True)
            return { 'message' : 'success', "invoices" : serializer.data, 'in_arrears': principal.school.in_arrears }
        
        except CustomUser.DoesNotExist:
            return {"error" : "user with the provided credentials can not be found"}
        
        except Exception as e:
            # if any exceptions rise during return the response return it as the response
            return {"error": str(e)}
       
       
    @database_sync_to_async
    def search_bug_report(self, bug_report_id):

        try:
            report = BugReport.objects.get(bugreport_id=bug_report_id)
            
            if report.status == "RESOLVED":
                serializer = ResolvedBugReportSerializer(instance=report)
                
            else:
                serializer = UnresolvedBugReportSerializer(instance=report)
            
            return { "report" : serializer.data}
        
        except BugReport.DoesNotExist:
            return {"error" : "bug report with the provided credentials can not be found"}
        
        except Exception as e:
            # if any exceptions rise during return the response return it as the response
            return {"error": str(e)} 
        
        
    @database_sync_to_async
    def search_principal_invoice(self, invoice_id):

        try:
            # Get the bill instance
            bill = Bill.objects.get(bill_id=invoice_id)
            
            # Serialize the bill
            serializer = BillSerializer(instance=bill)
            return { "invoice" : serializer.data }
        
        except Bill.DoesNotExist:
            return {"error" : "a bill with the provided ID does not exist"}
        
        except Exception as e:
            # if any exceptions rise during return the response return it as the response
            return {"error": str(e)}
        
        
    @database_sync_to_async
    def create_school_account(self, details):

        try:
            serializer = SchoolCreationSerializer(data=details)
            if serializer.is_valid():
                serializer.save()
                
                return { "message" : "school account created successfully" }
        
            return {"error" : serializer.errors}
        
        except Exception as e:
            return {'error': str(e)}
       
        
    @database_sync_to_async
    def delete_school_account(self, school_id):

        try:
            school = School.objects.get(school_id=school_id)
            school.delete()
            
            return {"message" : "school account deleted successfully"}
        
        except School.DoesNotExist:
            return {"error" : "school with the provided credentials can not be found"}
        
        except Exception as e:
            return {'error': str(e)}
        

    @database_sync_to_async
    def create_principal_account(self, details, school_id):

        try:
            # try to get the school instance
            school = School.objects.get(school_id=school_id)
    
            # Check if the school already has a principal
            if CustomUser.objects.filter(school=school, role="PRINCIPAL").exists():
                return {"error" : "school already has a principal account linked to it"}
        
            # Add the school instance to the request data
            details['school'] = school.id
            details['role'] = 'PRINCIPAL'
            
            serializer = PrincipalCreationSerializer(data=details)
        
            if serializer.is_valid():

                # Extract validated data
                validated_data = serializer.validated_data
                
                with transaction.atomic():
                    user = CustomUser.objects.create_user(**validated_data) 
                
                    # Create a new Balance instance for the user
                    Balance.objects.create(user=user)
            
                return {"message": "principal account created successfully", "user" : user}
            
            return {"error" : serializer.errors}
            
        except School.DoesNotExist:
            return {"error" : "school with the provided credentials can not be found"}
        
        except Exception as e:
            return {"error": str(e)}
        
        
    @database_sync_to_async
    def delete_principal_account(self, principal_id):

        try:
            principal = CustomUser.objects.get(account_id=principal_id, role='PRINCIPAL')
            principal.delete()
            
            return {"message" : "principal account deleted successfully"}
        
        except CustomUser.DoesNotExist:
            return {"error" : "principal with the provided credentials does not exist"}
        
        except Exception as e:
            return {'error': str(e)}


    @database_sync_to_async
    def fetch_schools(self):

        try:
            schools = School.objects.all().annotate(
                students=Count('users', filter=models.Q(users__role='STUDENT')),
                parents=Count('users', filter=models.Q(users__role='PARENT')),
                teachers=Count('users', filter=models.Q(users__role='TEACHER'))
            )
            
            serializer = SchoolsSerializer(schools, many=True)
            return { 'schools' : serializer.data }
        
        except Exception as e:
            return { 'error': str(e) }
        
        
    @database_sync_to_async
    def search_school(self, school_id):
        
        try:
            school = School.objects.get(school_id=school_id)
            serializer = SchoolSerializer(instance=school)
        
            return {"school" : serializer.data}
        
        except School.DoesNotExist:
            return {"error" : "school with the provided credentials can not be found"}
        
        except Exception as e:
            return {"error" : str(e)}
        
        
    @database_sync_to_async
    def search_school_details(self, school_id):
        
        try:
            school = School.objects.filter(school_id=school_id).annotate(
                students=Count('users', filter=Q(users__role='STUDENT')),
                parents=Count('users', filter=Q(users__role='PARENT')),
                teachers=Count('users', filter=Q(users__role='TEACHER')),
                admins=Count('users', filter=Q(users__role='ADMIN') | Q(users__role='PRINCIPAL')),
            )
            serializer = SchoolDetailsSerializer(school, many=True)
        
            return {"school" : serializer.data[0]}
        
        except School.DoesNotExist:
            return {"error" : "school with the provided credentials can not be found"}
        
        except Exception as e:
            return {"error" : str(e)}


    @database_sync_to_async
    def search_bug_reports(self, resolved):

        try:
            if resolved == True:
                reports = BugReport.objects.filter(status="RESOLVED").order_by('-created_at')
            else:
                reports = BugReport.objects.exclude(status="RESOLVED").order_by('-created_at')
                 
            serializer = BugReportsSerializer(reports, many=True)
            
            return { "reports" : serializer.data }
        
        except Exception as e:
            return { 'error': str(e) }
        
        
    async def send_email(self, user):
        mailgun_api_url = "https://api.eu.mailgun.net/v3/" + config('MAILGUN_DOMAIN') + "/messages"
        email_data = {
            "from": "seeran grades <accounts@" + config('MAILGUN_DOMAIN') + ">",
            "to": user.surname.title() + " " + user.name.title() + "<" + user.email + ">",
            "subject": "Account Creation Confirmation",
            "template": "account creation confirmation",
        }
        headers = {
            "Authorization": "Basic " + base64.b64encode(f"api:{config('MAILGUN_API_KEY')}".encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post( mailgun_api_url, headers=headers, data=email_data )
            
        if response.status_code == 200:
            return {"message": "principal account created successfully"}
            
        else:
            return {"error": "failed to send OTP to users email address"}
