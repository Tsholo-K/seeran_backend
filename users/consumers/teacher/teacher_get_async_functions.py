# python 

# httpx

# channels
from channels.db import database_sync_to_async

# django
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.dateparse import parse_time

# simple jwt

# models 
from users.models import Teacher
from schedules.models import Session, Schedule, TeacherSchedule, GroupSchedule
from grades.models import Grade
from classes.models import Classroom

# serilializers
from schedules.serializers import ScheduleSerializer
from classes.serializers import ClassSerializer, TeacherClassesSerializer, TeacherRegisterClassSerializer

# utility functions 



    