# python
import uuid

# rest framework
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

# django
from django.db import transaction
from django.core.cache import cache

# custom decorators
from authentication.decorators import token_required

# models 
from accounts.models import BaseAccount

# serializers
from accounts.serializers.general_serializers import ProfilePictureSerializer

# utility functions 
from accounts import utils as accounts_utilities


# user profile pictures upload 
@api_view(['PATCH'])
@parser_classes([MultiPartParser, FormParser])
@token_required
def update_profile_picture(request):
   
    profile_picture = request.FILES.get('profile_picture', None)
 
    if not profile_picture:
        return Response({"error" : "Could not process your request, no profile picture was uploaded."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        requesting_account = BaseAccount.objects.get(account_id=request.user.account_id)  # get the current user

        serializer = ProfilePictureSerializer(data={'profile_picture': profile_picture})
        if serializer.is_valid():
            with transaction.atomic():
                # Delete the old profile picture from GCS if it exists
                if requesting_account.profile_picture:
                    accounts_utilities.delete_profile_picture_from_gcs(requesting_account.profile_picture.name)

                # Generate a new filename
                ext = profile_picture.name.split('.')[-1]  # Get the file extension
                filename = f'{uuid.uuid4()}.{ext}'  # Create a new filename using a UUID

                # Upload the new profile picture to GCS
                accounts_utilities.upload_profile_picture_to_gcs(filename, profile_picture)

                # Update the user's profile picture field
                requesting_account.profile_picture.name = f"profile_pictures/{filename}"
                requesting_account.save()

                if cache.get(requesting_account.account_id + 'profile_picture'):
                    cache.delete(requesting_account.account_id + 'profile_picture')
                
            singed_url = accounts_utilities.generate_signed_url(filename)
            cache.set(requesting_account.account_id + 'profile_picture', singed_url, timeout=3600) 

            return Response({"profile_picture" : singed_url}, status=status.HTTP_200_OK)

        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        return Response({"error": error_response}, status=status.HTTP_400_BAD_REQUEST)
        
    except BaseAccount.DoesNotExist:
        return Response({"error" : "Could not process your request, an account with the provided credentials does not exist."}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    