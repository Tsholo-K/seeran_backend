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

# models
from .models import School

# serializers
from .serializers import SchoolCreationSerializer, SchoolsSerializer, SchoolSerializer, SchoolDetailsSerializer

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
        
        return Response({ "message" : "school account created successfully" }, status=201)
   
    return Response({"error" : serializer.errors})


@api_view(['GET'])
@token_required
@founder_only
def schools(request):
   
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
@token_required
@founder_only
def school(request, school_id):

    try:
        school = School.objects.get(school_id=school_id)
        serializer = SchoolSerializer(instance=school)
      
        return Response({"school" : serializer.data}, status=200)
 
    except Exception as e:
        return Response({"error" : str(e)}, status=500)


@api_view(['GET'])
@token_required
@founder_only
def school_details(request, school_id):
 
    try:
        school = School.objects.get(school_id=school_id)
        serializer = SchoolDetailsSerializer(instance=school)
    
        return Response({"school" : serializer.data}, status=200)
 
    except Exception as e:
        return Response({"error" : str(e)}, status=500)
