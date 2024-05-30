# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

# custom decorators
from authentication.decorators import token_required
from users.decorators import admins_only

# serilializers
from .serializers import ClassesSerializer

# models
from users.models import CustomUser
from grades.models import Grade



###################################### admindashboard views ###########################################


# get teachers classes
@api_view(['GET'])
@token_required
@admins_only
def teacher_classes(request, user_id):
    
    # try to get the user instance
    try:
        user = CustomUser.objects.get(user_id=user_id)
 
    except CustomUser.DoesNotExist:
        return Response({"error" : "user with the provided credentials does not exist"}, status=status.HTTP_404_NOT_FOUND)
    
    if request.user.school != user.school or user.role != 'TEACHER':
        return Response({ "error" : 'permission denied' }, status=status.HTTP_400_BAD_REQUEST)
    
    teachers_classes = user.taught_classes.all()

    # Serialize the data
    serializer = ClassesSerializer(teachers_classes, many=True)
    
    # Return the response
    return Response(serializer.data)


# get all register classes in a specific grade
@api_view(['GET'])
@token_required
@admins_only
def register_classes(request, grade):
    
    # try to get the grade instance
    try:
        grade_level = Grade.objects.get(grade=grade, school=request.user.school)
 
    except Grade.DoesNotExist:
        return Response({"error" : "grade with the provided level does not exist"}, status=status.HTTP_404_NOT_FOUND)
    
    # Filter the register classes
    classes = grade_level.grade_classes.filter(register_class=True)

    # Serialize the data
    serializer = ClassesSerializer(classes, many=True)
    
    # Return the response
    return Response(serializer.data)


################################################################################################
