# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

# custom decorators
from authentication.decorators import token_required
from users.decorators import admins_only

# serilializers
from .serializers import ScheduleDaysSerializer, SessoinsSerializer

# models
from users.models import CustomUser
from .models import Schedule



######################################### admindashboard views ###########################################


# get teachers schedule days 
@api_view(['GET'])
@token_required
@admins_only
def teacher_schedule_days(request, account_id):
    
    # try to get the user instance
    try:
        user = CustomUser.objects.get(account_id=account_id)
 
    except CustomUser.DoesNotExist:
        return Response({"error" : "user with the provided account ID does not exist"}, status=status.HTTP_404_NOT_FOUND)
    
    if request.user.school != user.school or user.role != 'TEACHER':
        return Response({ "error" : 'permission denied' }, status=status.HTTP_400_BAD_REQUEST)
    
    schedule_days = user.teacher_schedule.schedules.all().values('day', 'schedule_id')
    serializer = ScheduleDaysSerializer(schedule_days, many=True)
    
    # Return the response
    return Response({ "days" : serializer.data }, status=status.HTTP_200_OK)


# get a schedules sessions 
@api_view(['GET'])
@token_required
@admins_only
def schedule_sessions(request, schedule_id):
    
    # try to get the user instance
    try:
        schedule = Schedule.objects.get(schedule_id=schedule_id)
 
    except Schedule.DoesNotExist:
        return Response({"error" : "schedule with the provided ID does not exist"}, status=status.HTTP_404_NOT_FOUND)
    
    sessions = schedule.sessions.all()
    serializer = SessoinsSerializer(sessions, many=True)
    
    # Return the response
    return Response({ "sessions" : serializer.data }, status=status.HTTP_200_OK)


#########################################################################################################
