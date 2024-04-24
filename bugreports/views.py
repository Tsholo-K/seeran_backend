# django
from django.views.decorators.cache import cache_control
from django.shortcuts import get_object_or_404

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
from .serializers import CreateBugReportSerializer, BugReportsSerializer, BugReportSerializer, UpdateBugReportStatusSerializer


# create bug report
@api_view(['POST'])
@token_required
def create_bug_report(request):
    if request.user.role == "FOUNDER":
        return Response({"denied" : "come on dude"})
    data = request.data.copy()
    data['user'] = request.user.id
    serializer = CreateBugReportSerializer(data=data)
    if serializer.is_valid():
        try:
            serializer.save()
            return Response({"message" : "bug report submitted successfully"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            # if any exceptions rise during return the response, return it as the response
            return Response({"error": f"{str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response({"error" : serializer.errors})
    
    
# get bug reports
@api_view(["GET"])
@cache_control(max_age=120, private=True)
@token_required
@founder_only
def bug_reports(request, invalidator):
    reports = BugReport.objects.exclude(status="RESOLVED")
    serializer = BugReportsSerializer(reports, many=True)
    return Response({ "reports" : serializer.data },status=200)


# get users id info
@api_view(["GET"])
@cache_control(max_age=0, private=True)
@token_required
@founder_only
def bug_report(request, bug_report_id):
    report = BugReport.objects.get(bugreport_id=bug_report_id)
    serializer = BugReportSerializer(instance=report)
    return Response({ "report" : serializer.data },status=200)


# change bug report status
@api_view(["POST"])
@token_required
@founder_only
def update_bug_report_status(request, bug_report_id):
    bug_report = get_object_or_404(BugReport, bugreport_id=bug_report_id)
    serializer = UpdateBugReportStatusSerializer(bug_report, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({ "message" : "bug report status successfully changed" }, status=200)
    else:
        return Response({ "error" : serializer.errors }, status=status.HTTP_400_BAD_REQUEST)
