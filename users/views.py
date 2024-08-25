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
from users.models import Founder,Principal, Admin, Teacher, Student, Parent
from chats.models import ChatRoomMessage
from announcements.models import Announcement

# serilializers
from users.serializers.founders.founders_serializers import FounderAccountDetailsSerializer
from users.serializers.principals.principals_serializers import PrincipalAccountDetailsSerializer
from users.serializers.admins.admins_serializers import AdminAccountDetailsSerializer
from users.serializers.teachers.teachers_serializers import TeacherAccountDetailsSerializer
from users.serializers.students.students_serializers import StudentAccountDetailsSerializer
from users.serializers.parents.parents_serializers import ParentAccountDetailsSerializer


@api_view(["GET"])
@token_required
def my_account_details(request):
    """
    View to return the account details of the authenticated user along with unread messages
    and unread announcements count based on their role.

    - If the user is a FOUNDER, return founder-specific details.
    - If the user is a PARENT, PRINCIPAL, ADMIN, TEACHER, or STUDENT, return role-specific details.
    - For PARENTS, fetch announcements relevant to their children's schools.
    - For PRINCIPALS, ADMINs, TEACHERs, and STUDENTs, fetch announcements relevant to their school.
    - For TEACHERs, STUDENTs, ADMINs, and PRINCIPALS, serialize and return the appropriate details.
    - If the user's role is invalid, return an error response.

    Args:
        request (Request): The request object containing user information.

    Returns:
        Response: A JSON response containing user details, unread messages count,
        unread announcements count, or an error message.
    """

    # Ensure the user is authenticated
    if request.user:
        role = request.user.role

        if role not in ['FOUNDER', 'PARENT', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT']:
            return Response({"error": "your request could not be processed, your account has an invalid role"}, status=status.HTTP_401_UNAUTHORIZED)

        # Fetch the corresponding child model based on the user's role
        if role == 'FOUNDER':
            user = Founder.objects.get(account_id=request.user.account_id)
        elif role == 'PRINCIPAL':
            user = Principal.objects.get(account_id=request.user.account_id)
        elif role == 'ADMIN':
            user = Admin.objects.get(account_id=request.user.account_id)
        elif role == 'TEACHER':
            user = Teacher.objects.get(account_id=request.user.account_id)
        elif role == 'STUDENT':
            user = Student.objects.get(account_id=request.user.account_id)
        elif role == 'PARENT':
            user = Parent.objects.get(account_id=request.user.account_id)

        # Handle FOUNDER-specific serialization
        if role == 'FOUNDER':
            serialized_account = FounderAccountDetailsSerializer(instance=user).data
            return Response({'user': serialized_account}, status=status.HTTP_200_OK)

        # Determine unread announcements based on user role
        elif role == 'PARENT':
            # Fetch announcements for the schools the parent's children are enrolled in
            children_schools = user.children.values_list('school', flat=True)
            unread_announcements = Announcement.objects.filter(school__in=children_schools).exclude(reached=request.user).count()
            serialized_account = ParentAccountDetailsSerializer(instance=user).data

        else:
            # Handle specific role-based serialization
            role_serialization_mapping = {
                'PRINCIPAL': PrincipalAccountDetailsSerializer(instance=user).data,
                'ADMIN': AdminAccountDetailsSerializer(instance=user).data,
                'TEACHER': TeacherAccountDetailsSerializer(instance=user).data,
                'STUDENT': StudentAccountDetailsSerializer(instance=user).data
            }

            if user.school.none_compliant:
                return Response({"denied": "access denied"}, status=status.HTTP_403_FORBIDDEN)

            serialized_account = role_serialization_mapping[role]

            # Fetch announcements relevant to the user's school
            unread_announcements = user.school.announcements.exclude(reached=request.user).count()

        # Fetch unread messages for the user
        unread_messages = ChatRoomMessage.objects.filter(Q(chat_room__user_one=request.user) | Q(chat_room__user_two=request.user), read_receipt=False).exclude(sender=request.user).count()

        # Return the serialized account details along with unread counts
        return Response({'user': serialized_account, 'messages': unread_messages, 'announcements': unread_announcements}, status=status.HTTP_200_OK)

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

    