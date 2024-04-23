# django
from django.views.decorators.cache import cache_control

# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

# custom decorators
from authentication.decorators import token_required
from users.decorators import founder_only

# models 
from .models import BugReport
from users.models import CustomUser

# serializers
from .serializers import CreateBugReportSerializer



@api_view(['POST'])
@token_required
def create_bug_report(request):
    try:
        # Get the school instance
        user = CustomUser.objects.get(account_id=request.user.account_id)
    except CustomUser.DoesNotExist:
        return Response({"error" : "access denied"})
    data = request.data.copy()
    data['user'] = user
    serializer = CreateBugReportSerializer(data=data)
    if serializer.is_valid():
        try:
            serializer.save()
            return Response({"message" : "bug report submitted successfully"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            # if any exceptions rise during return the response, return it as the response
            return Response({"error": f"{str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response({"error" : "invalid information"})