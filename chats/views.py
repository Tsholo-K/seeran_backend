# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

# custom decorators
from authentication.decorators import token_required


###################################### admindashboard views ###########################################


# get teachers classes
@api_view(['GET'])
@token_required
def hi(request):
    
    # Return the response
    return Response({ "message" : 'hi' }, status=status.HTTP_201_CREATED)