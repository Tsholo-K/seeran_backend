# python 
import random

# django
from django.views.decorators.cache import cache_control
from django.db.models import Count
from django.db import models

# boto

# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response

# amazon email sending service
import boto3

# models
from .models import School
from balances.models import Balance
from users.models import CustomUser

# serializers
from .serializers import SchoolCreationSerializer, SchoolsSerializer, SchoolSerializer
from balances.serializers import BalanceSerializer

# custom decorators
from authentication.decorators import token_required
from users.decorators import founder_only

# utility functions


@api_view(['POST'])
@token_required
@founder_only
def create_school(request):
    serializer = SchoolCreationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        
        # Generate a random 6-digit number
        # this will invalidate the cache on the frontend
        random_number = random.randint(100000, 999999)
        return Response({ "message" : serializer.data, "invalidator" : random_number }, status=201)
    return Response({"error" : serializer.errors})


@api_view(['GET'])
@cache_control(max_age=0, private=True)
@token_required
@founder_only
def schools(request, invalidator):
    try:
        schools = School.objects.all().annotate(
            students=Count('users', filter=models.Q(users__role='STUDENT')),
            parents=Count('users', filter=models.Q(users__role='PARENT')),
            teachers=Count('users', filter=models.Q(users__role='TEACHER'))
        )
        serializer = SchoolsSerializer(schools, many=True)
        return Response({"schools" : serializer.data}, status=200)
    except Exception as e:
        return Response({"error" : str(e)}, status=500)


@api_view(['GET'])
@cache_control(max_age=300, private=True)
@token_required
@founder_only
def school(request, school_id, invalidator):
    try:
        school = School.objects.get(school_id=school_id)
        serializer = SchoolSerializer(instance=school)
        return Response({"school" : serializer.data}, status=200)
    except Exception as e:
        return Response({"error" : str(e)}, status=500)
