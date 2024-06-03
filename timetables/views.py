# python 
import datetime

# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

# custom decorators
from authentication.decorators import token_required
from users.decorators import admins_only

# serilializers
from .serializers import SchedulesSerializer, SessoinsSerializer

# models
from users.models import CustomUser
from .models import Session, Schedule



########################################## admindashboard views ############################################


# get teachers schedule days 
@api_view(['GET'])
@token_required
@admins_only
def teacher_schedules(request, account_id):
    
    # try to get the user instance
    try:
        user = CustomUser.objects.get(account_id=account_id)
 
    except CustomUser.DoesNotExist:
        return Response({"error" : "user with the provided account ID does not exist"}, status=status.HTTP_404_NOT_FOUND)
    
    if request.user.school != user.school or user.role != 'TEACHER':
        return Response({ "error" : 'permission denied' }, status=status.HTTP_400_BAD_REQUEST)
    
    teacher_schedules = user.teacher_schedule.all()

    if not teacher_schedules.exists():
        return Response({"schedules": []}, status=status.HTTP_200_OK)

    schedules_data = []
    for teacher_schedule in teacher_schedules:
      
        schedules = teacher_schedule.schedules.all().values('day', 'schedule_id')
        serializer = SchedulesSerializer(schedules, many=True)
        schedules_data.append(serializer.data)
    
    return Response({"schedules": schedules_data}, status=status.HTTP_200_OK)


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


# create teacher schedule 
@api_view(['POST'])
@token_required
@admins_only
def create_schedule(request):

    return Response({ 'schedule' : request.data })

    # Assuming the request body is JSON and contains the schedule data
    schedule_data = request.data
    
    # Create a new Schedule object for Monday
    schedule = Schedule(day='MONDAY')
    schedule.save()  # Save to generate a unique schedule_id
    
    # Iterate over the sessions in the provided data
    for session_info in schedule_data:
        # Convert the start and end times to Time objects
        start_time = datetime.time(
            hour=session_info['startTime']['hour'],
            minute=session_info['startTime']['minute'],
            second=session_info['startTime']['second']
        )
        end_time = datetime.time(
            hour=session_info['endTime']['hour'],
            minute=session_info['endTime']['minute'],
            second=session_info['endTime']['second']
        )
        
        # Create a new Session object
        session = Session(
            type=session_info['class'],
            classroom=session_info.get('classroom'),  # Using .get() in case 'classroom' is not provided
            session_from=start_time,
            session_till=end_time
        )
        session.save()
        
        # Add the session to the schedule's sessions
        schedule.sessions.add(session)
    
    # Save the schedule again to commit the added sessions
    schedule.save()
    
    # Return a success response
    return Response({'status': 'success', 'schedule_id': schedule.schedule_id})


###########################################################################################################
