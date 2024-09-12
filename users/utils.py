# channels
from channels.db import database_sync_to_async

# models
from users.models import Principal, Admin, Teacher, Student, Parent

# queries
from users.complex_queries import queries

# mappings
from users.maps import role_specific_maps


@database_sync_to_async
def get_account_and_security_details(user, role):
    try:
        Model, Serializer = role_specific_maps.account_model_and_security_details_serializer_mapping[role]
        return  Serializer(Model.objects.get(account_id=user)).data

    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a student account with the provided credentials does not exist, please check your account details and try again'}
               
    except Parent.DoesNotExist:
        # Handle the case where the requested parent account does not exist.
        return {'error': 'a parent account with the provided credentials does not exist, please check your account details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}

@database_sync_to_async
def get_account_and_linked_school(user, role):
    try:
        Model = role_specific_maps.account_access_control_mapping.get(role)
        return Model.objects.select_related('school').only('school').get(account_id=user)

    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a student account with the provided credentials does not exist, please check your account details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}

@database_sync_to_async
def get_account_and_attr(user, role):
    try:
        # Get the model, select_related, and prefetch_related fields based on the requested user's role.
        Model, select_related, prefetch_related = role_specific_maps.account_model_and_attr_mapping[role]

        # Retrieve the requested user's account from the database.
        return queries.account_and_its_attr_query_build(Model, select_related, prefetch_related).get(account_id=user)

    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a student account with the provided credentials does not exist, please check your account details and try again'}
               
    except Parent.DoesNotExist:
        # Handle the case where the requested parent account does not exist.
        return {'error': 'a parent account with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}