# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response

# models

# serializers
from .serializers import SchoolSerializer

# custom decorators
from authentication.decorators import token_required
from .decorators import founder_only


@api_view(['POST'])
@token_required
@founder_only
def create_school(request):
    serializer = SchoolSerializer(data=request.data)
    if serializer.is_valid():
        #serializer.save()
        return Response({"message" : serializer.data}, status=201)
    return Response({"error" : serializer.errors})
