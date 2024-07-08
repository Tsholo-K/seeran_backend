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