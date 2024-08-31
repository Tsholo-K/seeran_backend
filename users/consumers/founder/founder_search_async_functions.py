# python

# channels
from channels.db import database_sync_to_async

# django

# models 
from users.models import Principal
from schools.models import School
from balances.models import Bill
from bug_reports.models import BugReport

# serializers
from users.serializers.principals.principals_serializers import PrincipalAccountSerializer, PrincipalAccountDetailsSerializer
from schools.serializers import SchoolSerializer
from balances.serializers import BillsSerializer, BillSerializer
from bug_reports.serializers import BugReportsSerializer, BugReportSerializer

    
@database_sync_to_async
def search_school(details):
    try:
        school = School.objects.get(school_id=details.get('school'))

        serialized_school = SchoolSerializer(instance=school).data

        return {"school": serialized_school}
    
    except School.DoesNotExist:
        return {"error": "a school with the provided credentials can not be found"}
    
    except Exception as e:
        return {"error": str(e)}
    

@database_sync_to_async
def search_principal_profile(details):
    try:
        principal = Principal.objects.get(account_id=details.get('principal'))

        serializer = PrincipalAccountSerializer(instance=principal)

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
        serialized_principal = PrincipalAccountDetailsSerializer(instance=account).data

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
        
        serialized_bills = BillsSerializer(principal_bills, many=True).data

        return {'message': 'success', "invoices": serialized_bills, 'in_arrears': principal.school.in_arrears}
    
    except Principal.DoesNotExist:
        return {"error": "user with the provided credentials can not be found"}
    
    except Exception as e:
        return {"error": str(e)}
    
    
@database_sync_to_async
def search_principal_invoice(details):
    try:
        bill = Bill.objects.get(bill_id=details.get('invoice'))

        serialized_invoice = BillSerializer(instance=bill).data

        return {"invoice": serialized_invoice}
    
    except Bill.DoesNotExist:
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
        
        serializer = BugReportSerializer(instance=report)
        
        return {"report": serializer.data}
    
    except BugReport.DoesNotExist:
        return {"error": "bug report with the provided credentials can not be found"}
    
    except Exception as e:
        return {"error": str(e)}


