# python 
import uuid
import urllib.parse

# rest framework
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

# django
from django.db.models import Q

# custom decorators
from authentication.decorators import token_required

# models
from chats.models import ChatRoomMessage
from announcements.models import Announcement

# serilializers
from .serializers import MyAccountDetailsSerializer


@api_view(["GET"])
@token_required
def my_account_details(request):
   
    # if the user is authenticated, return their profile information 
    if request.user:
        if request.user.role == 'FOUNDER':
            serializer = MyAccountDetailsSerializer(instance=request.user)
            return Response({'user' : serializer.data}, status=status.HTTP_200_OK)
        
        else:
            # Fetch announcements based on role
            if request.user.role == 'PARENT':
                children_schools = request.user.children.values_list('school', flat=True)
                unread_announcements = Announcement.objects.filter(school__in=children_schools).exclude(reached=request.user).count()

            elif request.user.role in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT']:
                unread_announcements = Announcement.objects.filter(school=request.user.school).exclude(reached=request.user).count()
            
            else:
                return Response({'error' : 'your request could not be proccessed, your accounts role is invalid'}, status=status.HTTP_401_UNAUTHORIZED)

            # Fetch unread messages
            unread_messages = ChatRoomMessage.objects.filter(Q(chat_room__user_one=request.user) | Q(chat_room__user_two=request.user), read_receipt=False).exclude(sender=request.user).count()

            # Serialize user data
            serializer = MyAccountDetailsSerializer(instance=request.user)
            return Response({'user' : serializer.data, 'messages' : unread_messages, 'announcements' : unread_announcements}, status=status.HTTP_200_OK)

    else:
        return Response({"error" : "unauthenticated",}, status=status.HTTP_401_UNAUTHORIZED)


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

    