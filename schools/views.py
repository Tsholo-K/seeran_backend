# python 

# django

# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response

# serializers
from .serializers import SchoolCreationSerializer

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
