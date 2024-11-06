# channels
from channels.db import database_sync_to_async

# django
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

# models 
from accounts.models import BaseAccount
from email_cases.models import Case


@database_sync_to_async
def verify_thread_response(account, details):

    try:        
        print("About to fetch thread case and send email")
        # Ensure 'thread' and 'type' are present in details and are valid
        
        if not {'thread', 'type', 'message'}.issubset(details):
            response = f'Could not process your request, the provided information is invalid for the action you are trying to perform. Please make sure to provide a valid thread ID, email type, response message and try again'
            return {'error': response}

        print("Attempting to fetch the case and email...")
        # Fetch the case and initial email
        case = Case.objects.get(case_id=details.get('thread'), type=details.get('type').upper())
        print("fetched thread")

        initial_email = case.initial_email

        if not initial_email:
            print(f"Could not process your request, this thread does not have an initial email. Cannnot reply to an unknown sender or recipient.")
            return {"error": f"Could not process your request, this thread does not have an initial email. Cannnot reply to an unknown sender or recipient."}

        # Assign to the user if the case has no assigned user
        if case.assigned_to and case.assigned_to.account_id != account:
            print(f"Could not process your request, this thread is assigned to someone else. You are not allowed to respond to this thread.")
            return {"error": f"Could not process your request, this thread is assigned to someone else. You are not allowed to respond to this thread."}
        
        print("verified assigned to")

        # Determine the correct recipient based on whether the initial email is incoming
        if initial_email.is_incoming:
            recipient = initial_email.sender
        else:
            recipient = initial_email.recipient
        
        return {"case": case, "initial_email": initial_email, "recipient": recipient, "message": details.get('message')}
    
    except BaseAccount.DoesNotExist:
        return {'error': 'invalid email address'}

    except ValidationError:
        return {"error": "invalid email address"}
        
    except Exception as e:
        return {"error": str(e)}



    
