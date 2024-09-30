# python 

# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

# django
from django.db.models import Q

# custom decorators
from authentication.decorators import token_required

# models
from accounts.models import Founder
from chat_rooms.models import PrivateChatRoom
from school_announcements.models import Announcement

# serilializers
from accounts.serializers.founders.founders_serializers import FounderAccountDetailsSerializer

# mappings
from accounts.mappings import serializer_mappings

# utility functions 
from accounts import utils as accounts_utilities


@api_view(["GET"])
@token_required
def my_account_details(request):
    # Ensure the user is authenticated
    if request.user:
        # Handle FOUNDER-specific serialization
        if request.user.role == 'FOUNDER':
            founder = Founder.objects.get(account_id=request.user.account_id)
            serialized_founder = FounderAccountDetailsSerializer(instance=founder).data
            return Response({'user': serialized_founder}, status=status.HTTP_200_OK)

        # Check if the role is valid
        elif request.user.role in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT', 'PARENT']:
            # Fetch the corresponding child model and serializer based on the user's role
            requesting_account = accounts_utilities.get_account_and_permission_check_attr(request.user.account_id, request.user.role)

            # Determine unread announcements based on user role
            if request.user.role == 'PARENT':
                # Fetch announcements for the schools the parent's children are enrolled in
                children_schools = requesting_account.children.values_list('school_id', flat=True)
                unread_announcements = Announcement.objects.filter(school__in=children_schools).exclude(reached=request.user).count()

            else:
                if requesting_account.school.none_compliant:
                    return Response({"denied": "access denied"}, status=status.HTTP_403_FORBIDDEN)
                # Fetch announcements relevant to the user's school
                unread_announcements = requesting_account.school.announcements.exclude(reached=request.user).count()

            # Fetch unread messages for the user
            unread_messages = PrivateChatRoom.objects.filter(Q(chat_room__user_one=request.user) | Q(chat_room__user_two=request.user), read_receipt=False).exclude(sender=request.user).count()
            
            Serializer = serializer_mappings.account_details[request.user.role]
            # Serialize the user
            serialized_account = Serializer(instance=requesting_account).data

            # Return the serialized account details along with unread counts
            return Response({'user': serialized_account, 'messages': unread_messages, 'announcements': unread_announcements}, status=status.HTTP_200_OK)

        # Handle case where role is not recognized
        else:
            return Response({"error": "your request could not be processed, your account has an invalid role"}, status=status.HTTP_401_UNAUTHORIZED)

    # Return an error if the user is not authenticated
    else:
        return Response({"error": "your request could not be processed, your account is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)



# user profile pictures upload 
# @api_view(['PATCH'])
# @parser_classes([MultiPartParser, FormParser])
# @token_required
# def update_profile_picture(request):
   
#     profile_picture = request.FILES.get('profile_picture', None)
 
#     if not profile_picture:
#         return Response({"error" : "No file was uploaded."}, status=status.HTTP_400_BAD_REQUEST)

#     try:
#         user = CustomUser.objects.get(account_id=request.user.account_id)  # get the current user

#         with transaction.atomic():
#             user.profile_picture.delete()  # delete the old profile picture if it exists

#             # Generate a new filename
#             ext = profile_picture.name.split('.')[-1]  # Get the file extension
#             filename = f'{uuid.uuid4()}.{ext}'  # Create a new filename using a UUID

#             # URL-encode the filename
#             filename = urllib.parse.quote(filename)

#             user.profile_picture.save(filename, profile_picture)  # save the new profile picture
#             user.save()

#         if cache.get(user.account_id + 'profile_picture'):
#             cache.delete(user.account_id + 'profile_picture')
        
#         else:
#             user.refresh_from_db()  # Refresh the user instance from the database

#             serializer = ProfilePictureSerializer(instance=user)
#             return Response({"profile_picture" : serializer.data}, status=status.HTTP_200_OK)
        
#     except CustomUser.DoesNotExist:
#         return Response({"error" : "user with the provided credentials does not exist"}, status=status.HTTP_404_NOT_FOUND)

#     except Exception as e:
#         # if any exceptions rise during return the response return it as the response
#         return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# remove users picture
# @api_view(['POST'])
# @token_required
# def remove_profile_picture(request):
     
#     try:
#         user = CustomUser.objects.get(account_id=request.user.account_id)  # get the current user

#     except CustomUser.DoesNotExist:
#         return Response({"error" : "user with the provided credentials does not exist"}, status=status.HTTP_404_NOT_FOUND)
    
#     try:
        
#         if user.profile_picture:
#             user.profile_picture.delete()  # delete the old profile picture if it exists

#         else:
#             return Response({"error" : 'you already dont have a custom profile picture to remove'}, status=status.HTTP_200_OK)
        
#         user.refresh_from_db()  # Refresh the user instance from the database

#         serializer = ProfilePictureSerializer(instance=user)
#         return Response({"profile_picture" : serializer.data}, status=status.HTTP_200_OK)
    
#     except Exception as e:

#         # if any exceptions rise during return the response return it as the response
#         return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    