# python 
import random

# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response

# django
from django.views.decorators.cache import cache_control

# custom decorators
from authentication.decorators import token_required
from schools.decorators import founder_only

# models
from users.models import CustomUser
from schools.models import School

# serilializer
from .serializers import PrincipalCreationSerializer


@api_view(['POST'])
@cache_control(max_age=120, private=True)
@token_required
@founder_only
def create_principal(request, school_id):
    try:
        # Get the school instance
        school = School.objects.get(school_id=school_id)
    except School.DoesNotExist:
        return Response({"error" : "School not found"})
    # Check if the school already has a principal
    if CustomUser.objects.filter(school=school, role="PRINCIPAL").exists():
        return Response({"error" : "This school already has a principal account linked to it"}, status=400)
    # Add the school instance to the request data
    data = request.data.copy()
    data['school'] = school.id
    data['role'] = "PRINCIPAL"

    serializer = PrincipalCreationSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        # Generate a random 6-digit number
        # this will invalidate the cache on the frontend
        random_number = random.randint(100000, 999999)
        return Response({ "message" : serializer.data, "invalidator" : random_number }, status=201)
    return Response({"error" : serializer.errors}, status=400)
