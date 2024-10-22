# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.core.exceptions import ValidationError

# models 
from accounts.models import Principal
from schools.models import School
from balances.models import Balance

# serializers
from accounts.serializers.principals.serializers import PrincipalAccountCreationSerializer
from schools.serializers import SchoolCreationSerializer


@database_sync_to_async
def create_school_account(details):
    """
    Asynchronously creates a new School account using the provided details.

    This function attempts to create a new School account by validating the provided details 
    through the `SchoolCreationSerializer`. If the data is valid, it creates the School record 
    within an atomic transaction to ensure data integrity. In case of any validation errors, 
    it returns a formatted error message. If an unexpected error occurs, it returns a general error message.

    Args:
        details (dict): A dictionary containing the data required to create a new School account.

    Returns:
        dict: A dictionary containing either a success message or an error message.
            - If successful, returns {"message": "school account created successfully"}.
            - If validation fails, returns {"error": "formatted validation errors"}.
            - If an exception occurs, returns {'error': str(e)} with the exception message.
    """
    try:
        # Serialize the provided details using the SchoolCreationSerializer
        serializer = SchoolCreationSerializer(data=details)
        
        if serializer.is_valid():
            # If the data is valid, create the School record within an atomic transaction
            with transaction.atomic():
                School.objects.create(**serializer.validated_data)

            # Return a success message
            return {"message": "A new school account has been created. Link a principal to fully activate the account for billing and usage."}
    
        # If the data is not valid, return the validation errors formatted as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
        
    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        # Handle any unexpected errors and return a general error message
        return {'error': str(e).lower()}


@database_sync_to_async
def create_principal_account(details):
    """
    Asynchronously creates a new Principal account for a given school.

    This function attempts to create a new Principal account for the specified School. 
    It first checks if the School already has a Principal associated with it. If not, 
    it validates the provided details and creates the Principal account within an atomic 
    transaction to ensure data integrity. If any validation errors or exceptions occur, 
    appropriate error messages are returned.

    Args:
        details (dict): A dictionary containing the data required to create a new Principal account, including the `school_id`.

    Returns:
        dict: A dictionary containing either the created user or an error message.
            - If successful, returns {"user": user} with the created Principal instance.
            - If the School already has a Principal, returns {"error": "could not process your request, the provided school already has a principal account linked to it"}.
            - If the School does not exist, returns {"error": "school with the provided credentials can not be found"}.
            - If validation fails, returns {"error": "formatted validation errors"}.
            - If an exception occurs, returns {"error": str(e).lower()} with the exception message in lowercase.
    """
    try:
        # Retrieve the School instance by school_id from the provided details
        school = School.objects.get(school_id=details.get('school'))

        # Check if the School already has a Principal account associated with it
        if school.principal.exists():
            return {"error": "could not process your request, the provided school already has a principal account linked to it"}

        # Add the School's primary key and role to the details
        details['school'] = school.pk
        details['role'] = 'PRINCIPAL'
        
        # Serialize the provided details using the PrincipalAccountCreationSerializer
        serializer = PrincipalAccountCreationSerializer(data=details)

        if serializer.is_valid():
            # Extract validated data
            validated_data = serializer.validated_data
            
            # Create the Principal account and associated Balance within an atomic transaction
            with transaction.atomic():
                user = Principal.objects.create(**validated_data)
                Balance.objects.create(user=user)
        
            # Return the created Principal user
            return {"user": user}
        
        # If the data is not valid, return the validation errors formatted as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
        
    except School.DoesNotExist:
        # Handle the case where the School does not exist
        return {"error": "a school with the provided credentials does not exist"}
    
    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {"error": str(e).lower()}

