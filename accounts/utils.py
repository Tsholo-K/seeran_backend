# models
from accounts.models import Principal, Admin, Teacher, Student, Parent

# queries
from seeran_backend.complex_queries import queries

# mappings
from accounts.mappings import model_mapping, serializer_mappings, attr_mappings


def get_account(account, role):
    try:
        Model = model_mapping.account[role]

        return Model.objects.get(account_id=account)

    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a principal account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, an admin account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a teacher account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a student account with the provided credentials does not exist. Please review your account details and try again.'}
               
    except Parent.DoesNotExist:
        # Handle the case where the requested parent account does not exist.
        return {'error': 'Could not process your request, a parent account with the provided credentials does not exist. Please review your account details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}

def get_account_and_security_information(account, role):
    try:
        Model = model_mapping.account[role]
        Serializer = serializer_mappings.account_security_information[role]

        requesting_account = Model.objects.get(account_id=account)

        return Serializer(requesting_account).data

    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a principal account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, an admin account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a teacher account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a student account with the provided credentials does not exist. Please review your account details and try again.'}
               
    except Parent.DoesNotExist:
        # Handle the case where the requested parent account does not exist.
        return {'error': 'Could not process your request, a parent account with the provided credentials does not exist. Please review your account details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}

def get_account_and_permission_check_attr(account, role):
    try:
        Model = model_mapping.account[role]
        select_related, prefetch_related = attr_mappings.permission_check[role]

        return queries.join_queries(Model, select_related, prefetch_related).get(account_id=account)

    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a principal account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, an admin account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a teacher account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a student account with the provided credentials does not exist. Please review your account details and try again.'}
               
    except Parent.DoesNotExist:
        # Handle the case where the requested parent account does not exist.
        return {'error': 'Could not process your request, a parent account with the provided credentials does not exist. Please review your account details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}

def get_account_and_linked_school(account, role):
    try:
        Model = model_mapping.account[role]

        return Model.objects.select_related('school').get(account_id=account)

    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a principal account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, an admin account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a teacher account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a student account with the provided credentials does not exist. Please review your account details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}

def get_account_and_creation_serializer(role):
    try:
        return (model_mapping.account[role], serializer_mappings.account_creation[role])

    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a principal account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, an admin account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a teacher account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a student account with the provided credentials does not exist. Please review your account details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
