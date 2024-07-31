from channels.db import database_sync_to_async

# django
from django.db.models import Count, Q
from django.db import models, transaction
from django.db import IntegrityError

# models 
from balances.models import Bill
from users.models import CustomUser
from schools.models import School
from balances.models import Balance
from bug_reports.models import BugReport

# serializers
from users.serializers import ProfileSerializer, PrincipalCreationSerializer, PrincipalIDSerializer, PrincipalAccountUpdateSerializer
from schools.serializers import SchoolCreationSerializer, SchoolsSerializer, SchoolSerializer, SchoolDetailsSerializer
from balances.serializers import BillsSerializer, BillSerializer
from bug_reports.serializers import BugReportsSerializer, UnresolvedBugReportSerializer, ResolvedBugReportSerializer, UpdateBugReportStatusSerializer



@database_sync_to_async
def create_principal_account(details, school_id):

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
        
            return {"user" : user}
        
        return {"error" : serializer.errors}
        
    except School.DoesNotExist:
        return {"error" : "school with the provided credentials can not be found"}
    
    except Exception as e:
        return {"error": str(e)}
    
    
@database_sync_to_async
def delete_principal_account(principal_id):

    try:
        principal = CustomUser.objects.get(account_id=principal_id, role='PRINCIPAL')
        principal.delete()
        
        return {"message" : "principal account deleted successfully"}
    
    except CustomUser.DoesNotExist:
        return {"error" : "principal with the provided credentials does not exist"}
    
    except Exception as e:
        return {'error': str(e)}
    
    
@database_sync_to_async
def search_principal_profile(principal_id):

    try:
        principal = CustomUser.objects.get(account_id=principal_id, role='PRINCIPAL')
        
        serializer = ProfileSerializer(instance=principal)
        return { "user" : serializer.data }
    
    except CustomUser.DoesNotExist:
        return { 'error': 'principal with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    
    
@database_sync_to_async
def search_account_id(account_id):

    try:
        account  = CustomUser.objects.get(account_id=account_id)

        if account.role != 'PRINCIPAL':
            return { "error" : 'unauthorized access.. permission denied' }

        # return the users profile
        serializer = PrincipalIDSerializer(instance=account)
        return { "user" : serializer.data }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def search_principal_invoices(principal_id):

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
def search_principal_invoice(invoice_id):

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
def search_bug_reports(resolved):

    try:
        if resolved == True:
            reports = BugReport.objects.filter(status="RESOLVED").order_by('-created_at')
        else:
            reports = BugReport.objects.exclude(status="RESOLVED").order_by('-created_at')
                
        serializer = BugReportsSerializer(reports, many=True)
        
        return { "reports" : serializer.data }
    
    except Exception as e:
        return { 'error': str(e) }
    
    
@database_sync_to_async
def search_bug_report(bug_report_id):

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
def update_bug_report(status, bug_report_id):
    
    try:
        bug_report = BugReport.objects.get(bugreport_id=bug_report_id)
        serializer = UpdateBugReportStatusSerializer(bug_report, data={status:status})
    
        if serializer.is_valid():
            bug_report.status = status
            bug_report.save()
            return { "message" : "bug report status successfully changed"}
    
        else:
            return { "error" : serializer.errors }
    
    except BugReport.DoesNotExist:
        return { 'error': 'bug report with the provided ID does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def update_account(updates, account_id):

    try:
        if updates.get('email') != (None or ''):
            if CustomUser.objects.filter(email=updates.get('email')).exists():
                return {"error": "an account with the provided email address already exists"}

        if updates.get('phone_number') != (None or ''):
            if CustomUser.objects.filter(phone_number=updates.get('phone_number'), role='PRINCIPAL').exists():
                return {"error": "an account with the provided phone number already exists"}
            
        account  = CustomUser.objects.get(account_id=account_id)

        if account.role == 'PRINCIPAL':
            return { "error" : 'unauthorized access.. permission denied' }
        
        serializer = PrincipalAccountUpdateSerializer(instance=account, data=updates)
        
        if serializer.is_valid():
            
            with transaction.atomic():
                serializer.save()
                account.refresh_from_db()  # Refresh the user instance from the database
            
            serializer = PrincipalIDSerializer(instance=account)
            return { "user" : serializer.data }
            
        return {"error" : serializer.errors}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def create_school_account(details):

    try:
        serializer = SchoolCreationSerializer(data=details)
        if serializer.is_valid():
            serializer.save()
            
            return { "message" : "school account created successfully" }
    
        return {"error" : serializer.errors}
    
    except Exception as e:
        return {'error': str(e)}
    
    
@database_sync_to_async
def delete_school_account(school_id):

    try:
        school = School.objects.get(school_id=school_id)
        school.delete()
        
        return {"message" : "school account deleted successfully"}
    
    except School.DoesNotExist:
        return {"error" : "school with the provided credentials can not be found"}
    
    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def fetch_schools():

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
def search_school(school_id):
    
    try:
        school = School.objects.get(school_id=school_id)
        serializer = SchoolSerializer(instance=school)
    
        return {"school" : serializer.data}
    
    except School.DoesNotExist:
        return {"error" : "school with the provided credentials can not be found"}
    
    except Exception as e:
        return {"error" : str(e)}
    
    
@database_sync_to_async
def search_school_details(school_id):
    
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
