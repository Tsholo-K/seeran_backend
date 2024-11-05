# python
import base64
import zlib
import json

# channels
from channels.db import database_sync_to_async

# models 
from accounts.models import Principal
from schools.models import School
from emails.models import Email
from email_cases.models import Case
from invoices.models import Invoice
from bug_reports.models import BugReport

# serializers
from accounts.serializers.principals.serializers import PrincipalAccountSerializer, PrincipalAccountDetailsSerializer
from schools.serializers import SchoolSerializer, SchoolDetailsSerializer
from email_cases.serializers import EmailCasesSerializer
from invoices.serializers import InvoiceSerializer, InvoicesSerializer
from bug_reports.serializers import BugReportsSerializer, BugReportSerializer


@database_sync_to_async
def search_threads(details):
    try:
        # Fetch all School records from the database
        threads = Case.objects.filter(type=details.get('type').upper(), status=details.get('status').upper())
        
        # Serialize the fetched schools data
        serialized_threads = EmailCasesSerializer(threads, many=True).data

        # Compress the serialized data
        compressed_threads = zlib.compress(json.dumps(serialized_threads).encode('utf-8'))

        # Encode compressed data as base64 for safe transport
        encoded_threads = base64.b64encode(compressed_threads).decode('utf-8')

        # Return the serialized data in a dictionary
        return {'threads': encoded_threads}

    except Exception as e:
        # Handle any unexpected errors and return a general error message
        return {'error': str(e)}

    
@database_sync_to_async
def search_school(details):
    try:
        school = School.objects.get(school_id=details.get('school'))

        serialized_school = SchoolSerializer(school).data

        return {"school": serialized_school}
    
    except School.DoesNotExist:
        return {"error": "a school with the provided credentials can not be found"}
    
    except Exception as e:
        return {"error": str(e)}
    
    
@database_sync_to_async
def search_school_details(details):
    try:
        school = School.objects.get(school_id=details.get('school'))

        # Serialize the school object into a dictionary
        serialized_school = SchoolDetailsSerializer(school).data

        return {"school": serialized_school}

    except School.DoesNotExist:
        # Handle the case where the provided school ID does not exist
        return {"error": "a school with the provided credentials does not exist"}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
    

@database_sync_to_async
def search_principal_profile(details):
    try:
        principal = Principal.objects.get(account_id=details.get('principal'))

        serializer = PrincipalAccountSerializer(principal)

        return {"principal": serializer.data}
    
    except Principal.DoesNotExist:
        return {'error': 'principal with the provided credentials does not exist'}
    
    except Exception as e:
        return {'error': str(e)}

    
@database_sync_to_async
def search_principal_details(details):
    try:
        account = Principal.objects.get(account_id=details.get('account'))

        # Return the user's profile
        serialized_principal = PrincipalAccountDetailsSerializer(account).data

        return {"principal": serialized_principal}
        
    except Principal.DoesNotExist:
        return {'error': 'account with the provided credentials does not exist'}
    
    except Exception as e:
        return {'error': str(e)}
    

@database_sync_to_async
def search_principal_invoices(details):
    try:
        principal = Principal.objects.prefetch_related('bills').get(account_id=details.get('principal'))
        principal_bills = principal.bills
        
        if not principal_bills:
            return {'message': 'success', "invoices": None, 'in_arrears': principal.school.in_arrears}
        
        serialized_bills = InvoicesSerializer(principal_bills, many=True).data

        return {'message': 'success', "invoices": serialized_bills, 'in_arrears': principal.school.in_arrears}
    
    except Principal.DoesNotExist:
        return {"error": "user with the provided credentials can not be found"}
    
    except Exception as e:
        return {"error": str(e)}
    
    
@database_sync_to_async
def search_principal_invoice(details):
    try:
        bill = Invoice.objects.get(Invoice_id=details.get('invoice'))

        serialized_invoice = InvoiceSerializer(bill).data

        return {"invoice": serialized_invoice}
    
    except Invoice.DoesNotExist:
        return {"error": "a bill with the provided ID does not exist"}
    
    except Exception as e:
        return {"error": str(e)}
    

@database_sync_to_async
def search_bug_reports(details):
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
    try:
        report = BugReport.objects.get(bugreport_id=details.get('bug_report'))
        
        serializer = BugReportSerializer(report)
        
        return {"report": serializer.data}
    
    except BugReport.DoesNotExist:
        return {"error": "bug report with the provided credentials can not be found"}
    
    except Exception as e:
        return {"error": str(e)}


