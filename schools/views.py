# python 

# django
from django.db.models import Count
from django.db import models
from django.db import transaction

# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

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


# delete school account
@api_view(['POST'])
@token_required
@founder_only
def delete_school(request):
   
    try:
        # Get the school instance
        with transaction.atomic():
            school = School.objects.get(school_id=request.data['school_id'])
            school.delete()
      
        return Response({"message" : "school account deleted successfully",}, status=status.HTTP_200_OK)
    
    except School.DoesNotExist:
        return Response({"error" : "school with the provided credentials can not be found"}, status=status.HTTP_404_NOT_FOUND)
 
    except Exception as e:
        # if any exceptions rise during return the response return it as the response
        return Response({"error": {str(e)}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)