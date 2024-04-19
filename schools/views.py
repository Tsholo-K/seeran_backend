# python 
import random

# django
from django.views.decorators.cache import cache_control

# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response

# models
from .models import School

# serializers
from .serializers import SchoolSerializer, SchoolsSerializer

# custom decorators
from authentication.decorators import token_required
from .decorators import founder_only


@api_view(['POST'])
@token_required
@founder_only
def create_school(request):
    serializer = SchoolSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        # Generate a random 6-digit number
        # this will invalidate the cache on the frontend
        random_number = random.randint(100000, 999999)
        return Response({ "message" : serializer.data, "invalidator" : random_number }, status=201)
    return Response({"error" : serializer.errors})


@api_view(['GET'])
@cache_control(max_age=86400, private=True)
@token_required
@founder_only
def schools(request):
    schools = School.objects.all()
    serializer = SchoolsSerializer(schools, many=True)
    response = Response({"schools" : serializer.data}, status=200)
    return response
