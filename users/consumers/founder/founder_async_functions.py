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
from users.serializers import AccountProfileSerializer, PrincipalAccountCreationSerializer, PrincipalIDSerializer, PrincipalAccountUpdateSerializer
from schools.serializers import SchoolCreationSerializer, SchoolsSerializer, SchoolSerializer, SchoolDetailsSerializer
from balances.serializers import BillsSerializer, BillSerializer
from bug_reports.serializers import BugReportsSerializer, BugReportSerializer, UpdateBugReportStatusSerializer


@database_sync_to_async
def create_school_account(details):
    """
    Creates a new school account.

    Args:
        details (dict): The details of the school to be created.

    Returns:
        dict: A dictionary containing either a success message or an error message.
    """
    try:
        serializer = SchoolCreationSerializer(data=details)
        if serializer.is_valid():
            serializer.save()
            return {"message": "school account created successfully"}
    
        return {"error": serializer.errors}
    
    except Exception as e:
        return {'error': str(e)}

    
@database_sync_to_async
def delete_school_account(details):
    """
    Deletes a school account by its ID.

    Args:
        school_id (str): The ID of the school to be deleted.

    Returns:
        dict: A dictionary containing either a success message or an error message.
    """
    try:
        school = School.objects.get(school_id=details.get('school_id'))
        school.delete()
        return {"message": "school account deleted successfully"}
    
    except School.DoesNotExist:
        return {"error": "school with the provided credentials can not be found"}
    
    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def fetch_schools():
    """
    Fetches all school accounts.

    Returns:
        dict: A dictionary containing the school accounts or an error message.
    """
    try:
        schools = School.objects.all().annotate(
            students=Count('users', filter=Q(users__role='STUDENT')),
            parents=Count('users', filter=Q(users__role='PARENT')),
            teachers=Count('users', filter=Q(users__role='TEACHER'))
        )
        
        serializer = SchoolsSerializer(schools, many=True)
        return {'schools': serializer.data}
    
    except Exception as e:
        return {'error': str(e)}

    
@database_sync_to_async
def search_school(details):
    """
    Searches for a school account by its ID.

    Args:
        school_id (str): The ID of the school.

    Returns:
        dict: A dictionary containing the school details or an error message.
    """
    try:
        school = School.objects.get(school_id=details.get('school_id'))
        serializer = SchoolSerializer(instance=school)
        return {"school": serializer.data}
    
    except School.DoesNotExist:
        return {"error": "school with the provided credentials can not be found"}
    
    except Exception as e:
        return {"error": str(e)}
    
    
@database_sync_to_async
def search_school_details(details):
    """
    Searches for detailed information about a school account by its ID.

    Args:
        school_id (str): The ID of the school.

    Returns:
        dict: A dictionary containing the detailed school information or an error message.
    """
    try:
        school = School.objects.filter(school_id=details.get('school_id')).annotate(
            students=Count('users', filter=Q(users__role='STUDENT')),
            parents=Count('users', filter=Q(users__role='PARENT')),
            teachers=Count('users', filter=Q(users__role='TEACHER')),
            admins=Count('users', filter=Q(users__role='ADMIN') | Q(users__role='PRINCIPAL')),
        )
        serializer = SchoolDetailsSerializer(school, many=True)
        return {"school": serializer.data[0]}
    
    except School.DoesNotExist:
        return {"error": "school with the provided credentials can not be found"}
    
    except Exception as e:
        return {"error": str(e)}
    

@database_sync_to_async
def create_principal_account(details):
    """
    Creates a principal account for a specified school.

    Args:
        details (dict): The details of the principal to be created.
        school_id (str): The ID of the school.

    Returns:
        dict: A dictionary containing either the created user or an error message.
    """
    try:
        # Try to get the school instance
        school = School.objects.get(school_id=details.get('school'))

        # Check if the school already has a principal
        if CustomUser.objects.filter(school=school, role="PRINCIPAL").exists():
            return {"error": "school already has a principal account linked to it"}

        # Add the school instance to the request data
        details['school'] = school.id
        details['role'] = 'PRINCIPAL'
        
        serializer = PrincipalAccountCreationSerializer(data=details)

        if serializer.is_valid():
            # Extract validated data
            validated_data = serializer.validated_data
            
            with transaction.atomic():
                user = CustomUser.objects.create_user(**validated_data) 
                # Create a new Balance instance for the user
                Balance.objects.create(user=user)
        
            return {"user": user}
        
        return {"error": serializer.errors}
        
    except School.DoesNotExist:
        return {"error": "school with the provided credentials can not be found"}
    
    except Exception as e:
        return {"error": str(e)}

    
@database_sync_to_async
def delete_principal_account(details):
    """
    Deletes a principal account.

    Args:
        principal_id (str): The ID of the principal to be deleted.

    Returns:
        dict: A dictionary containing either a success message or an error message.
    """
    try:
        principal = CustomUser.objects.get(account_id=details.get('principal_id'), role='PRINCIPAL')
        principal.delete()
        
        return {"message": "principal account deleted successfully"}
    
    except CustomUser.DoesNotExist:
        return {"error": "principal with the provided credentials does not exist"}
    
    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def update_principal_account(details):
    """
    Updates a principal account's details.

    Args:
        updates (dict): The updated details.
        account_id (str): The ID of the account to be updated.

    Returns:
        dict: A dictionary containing the updated user profile or an error message.
    """
    try:
        updates = details.get('updates')

        if updates.get('email'):
            if CustomUser.objects.filter(email=updates.get('email')).exists():
                return {"error": "an account with the provided email address already exists"}

        if updates.get('phone_number'):
            if CustomUser.objects.filter(phone_number=updates.get('phone_number'), role='PRINCIPAL').exists():
                return {"error": "an account with the provided phone number already exists"}
            
        account = CustomUser.objects.get(account_id=details.get('account_id'))

        if account.role != 'PRINCIPAL':
            return {"error": 'unauthorized access.. permission denied'}
        
        serializer = PrincipalAccountUpdateSerializer(instance=account, data=updates)
        
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()
                account.refresh_from_db()  # Refresh the user instance from the database
            
            serializer = PrincipalIDSerializer(instance=account)
            return {"user": serializer.data}
            
        return {"error": serializer.errors}
    
    except CustomUser.DoesNotExist:
        return {'error': 'account with the provided credentials does not exist'}
    
    except Exception as e:
        return {'error': str(e)}    
    

@database_sync_to_async
def search_principal_profile(details):
    """
    Searches for a principal's account profile by their account ID.

    Args:
        principal_id (str): The ID of the principal.

    Returns:
        dict: A dictionary containing the principal's profile or an error message.
    """
    try:
        principal = CustomUser.objects.get(account_id=details.get('principal_id'), role='PRINCIPAL')
        serializer = AccountProfileSerializer(instance=principal)
        return {"user": serializer.data}
    
    except CustomUser.DoesNotExist:
        return {'error': 'principal with the provided credentials does not exist'}
    
    except Exception as e:
        return {'error': str(e)}

    
@database_sync_to_async
def search_principal_id(details):
    """
    Searches for a principal's account ID by their account ID.

    Args:
        account_id (str): The ID of the account.

    Returns:
        dict: A dictionary containing the principal's ID or an error message.
    """
    try:
        account = CustomUser.objects.get(account_id=details.get('account_id'))

        if account.role != 'PRINCIPAL':
            return {"error": 'unauthorized access.. permission denied'}

        # Return the user's profile
        serializer = PrincipalIDSerializer(instance=account)
        return {"user": serializer.data}
        
    except CustomUser.DoesNotExist:
        return {'error': 'account with the provided credentials does not exist'}
    
    except Exception as e:
        return {'error': str(e)}
    

@database_sync_to_async
def search_principal_invoices(details):
    """
    Searches for all invoices associated with a principal.

    Args:
        principal_id (str): The ID of the principal.

    Returns:
        dict: A dictionary containing the invoices or an error message.
    """
    try:
        principal = CustomUser.objects.get(account_id=details.get('principal_id'))
        principal_bills = Bill.objects.filter(user=principal).order_by('-date_billed')
        
        if not principal_bills:
            return {'message': 'success', "invoices": None, 'in_arrears': principal.school.in_arrears}
        
        serializer = BillsSerializer(principal_bills, many=True)
        return {'message': 'success', "invoices": serializer.data, 'in_arrears': principal.school.in_arrears}
    
    except CustomUser.DoesNotExist:
        return {"error": "user with the provided credentials can not be found"}
    
    except Exception as e:
        return {"error": str(e)}
    
    
@database_sync_to_async
def search_principal_invoice(details):
    """
    Searches for a specific invoice by its ID.

    Args:
        invoice_id (str): The ID of the invoice.

    Returns:
        dict: A dictionary containing the invoice details or an error message.
    """
    try:
        bill = Bill.objects.get(bill_id=details.get('invoice_id'))
        serializer = BillSerializer(instance=bill)
        return {"invoice": serializer.data}
    
    except Bill.DoesNotExist:
        return {"error": "a bill with the provided ID does not exist"}
    
    except Exception as e:
        return {"error": str(e)}
    

@database_sync_to_async
def search_bug_reports(details):
    """
    Searches for all bug reports, optionally filtered by their resolution status.

    Args:
        resolved (bool): If True, only resolved reports are returned. Otherwise, unresolved reports are returned.

    Returns:
        dict: A dictionary containing the bug reports or an error message.
    """
    try:
        if details.get('resolved'):
            reports = BugReport.objects.filter(status="RESOLVED").order_by('-created_at')
        else:
            reports = BugReport.objects.exclude(status="RESOLVED").order_by('-created_at')
                
        serializer = BugReportsSerializer(reports, many=True)
        return {"reports": serializer.data}
    
    except Exception as e:
        return {'error': str(e)}
    
    
@database_sync_to_async
def search_bug_report(details):
    """
    Searches for a specific bug report by its ID.

    Args:
        bug_report_id (str): The ID of the bug report.

    Returns:
        dict: A dictionary containing the bug report details or an error message.
    """
    try:
        report = BugReport.objects.get(bugreport_id=details.get('bug_report_id'))
        
        serializer = BugReportSerializer(instance=report)
        
        return {"report": serializer.data}
    
    except BugReport.DoesNotExist:
        return {"error": "bug report with the provided credentials can not be found"}
    
    except Exception as e:
        return {"error": str(e)}
    
    
@database_sync_to_async
def update_bug_report(details):
    """
    Updates the status of a bug report.

    Args:
        status (str): The new status of the bug report.
        bug_report_id (str): The ID of the bug report.

    Returns:
        dict: A dictionary containing a success message or an error message.
    """
    try:
        bug_report = BugReport.objects.get(bugreport_id=details.get('bug_report_id'))
        serializer = UpdateBugReportStatusSerializer(bug_report, data={'status': details.get('status')})
    
        if serializer.is_valid():
            serializer.save()

            return {"message": "bug report status successfully changed"}
    
        else:
            return {"error": serializer.errors}
    
    except BugReport.DoesNotExist:
        return {'error': 'bug report with the provided ID does not exist'}
    
    except Exception as e:
        return {'error': str(e)}


