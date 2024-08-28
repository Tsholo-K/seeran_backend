# python 

# httpx

# channels
from channels.db import database_sync_to_async

# django

# simple jwt

# models 
from users.models import Principal, Admin

# serilializers
from grades.serializers import GradesSerializer
from schools.serializers import SchoolDetailsSerializer

# mappings
from users.maps import role_specific_maps

# queries
from users.complex_queries import queries


@database_sync_to_async
def fetch_grades(user, role):

    try:
        # Get the appropriate model for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = Model.objects.select_related('school').prefetch_related('school__grades').only('school').get(account_id=user)
            
        grades = requesting_account.school.grades.all()

        # Serialize the grade objects into a dictionary
        serialized_grades = GradesSerializer(grades, many=True).data

        return {'grades': serialized_grades}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


    