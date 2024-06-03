# django 
from django.utils.dateparse import parse_time
from django.core.exceptions import ValidationError
from django.db import transaction

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
from .models import Session, Schedule, TeacherSchedule



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


# create schedule 
@api_view(['POST'])
@token_required
@admins_only
def create_schedule(request):

    try:

        # Extract the 'sessions' list from the nested 'schedule' dictionary
        sessions = request.data.get('sessions', [])
        
        # Extract the day of the schedule from the nested 'schedule' dictionary
        day_of_week = request.data.get('day', '').upper()

        # Extract the account id from the nested 'schedule' dictionary
        account_id = request.data.get('account', None)

        if not sessions or not day_of_week or not account_id:
            return Response({ "error" : 'missing information' }, status=status.HTTP_400_BAD_REQUEST)

        if day_of_week not in [ 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']:
            return Response({ "error" : 'invalid schedule day' }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():

            # Retrieve the user instance using the provided account ID
            teacher = CustomUser.objects.get(account_id=account_id)
            
            schedule = Schedule(day=day_of_week)
            schedule.save()  # Save to generate a unique schedule_id
            
            # Iterate over the sessions in the provided data
            for session_info in sessions:
                
                # Convert the start and end times to Time objects
                start_time = parse_time(f"{session_info['startTime']['hour']}:{session_info['startTime']['minute']}:{session_info['startTime']['second']}")
                end_time = parse_time(f"{session_info['endTime']['hour']}:{session_info['endTime']['minute']}:{session_info['endTime']['second']}")
                
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

            # Check if the teacher already has a schedule for the provided day
            existing_teacher_schedule = TeacherSchedule.objects.filter(teacher=teacher, schedules__day=day_of_week)

            for schedules in existing_teacher_schedule:
                # Remove the specific schedules for that day
                schedules.schedules.filter(day=day_of_week).delete()

            # Check if the teacher already has a TeacherSchedule object
            teacher_schedule, created = TeacherSchedule.objects.get_or_create(teacher=teacher)

            # If the object was created, a new unique teacher_schedule_id will be generated
            if created:
                teacher_schedule.save()

            # Add the new schedule to the teacher's schedules
            teacher_schedule.schedules.add(schedule)

            # Save the TeacherSchedule object to commit any changes
            teacher_schedule.save()
        
    except CustomUser.DoesNotExist:
        return Response({"error": "account with the provided account ID does not exist"}, status=status.HTTP_404_NOT_FOUND)

    except ValidationError as e:
        # Handle specific known validation errors
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        # Handle unexpected errors
        return Response({'error': 'An unexpected error occurred'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Return a success response
    return Response({'message': 'schedule successfully created'}, status=status.HTTP_201_CREATED)

###########################################################################################################
