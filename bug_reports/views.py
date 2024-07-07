# python 

# django
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

# serializers
from .serializers import CreateBugReportSerializer, BugReportsSerializer, UnresolvedBugReportSerializer, ResolvedBugReportSerializer, UpdateBugReportStatusSerializer, MyBugReportSerializer


################################################## general views ##########################################################


# create bug report
@api_view(['POST'])
@token_required
def create_bug_report(request):

    try:
        if request.user.role == "FOUNDER":
            return Response({"denied" : "come on dude"})
        
        data = request.data.copy()
        data['user'] = request.user.id
        serializer = CreateBugReportSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response({"message" : "bug report submitted successfully"}, status=status.HTTP_201_CREATED)
        
        else:
            return Response({"error" : serializer.errors})
        
    except Exception as e:
        # if any exceptions rise during return the response, return it as the response
        return Response({"error": f"{str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# get users bug reports
@api_view(["GET"])
@token_required
@founder_only
def my_bug_reports(request):
   
    report = BugReport.objects.get(user=request.user)
    serializer = BugReportsSerializer(instance=report)
    
    return Response({ "reports" : serializer.data},status=200)
 

# get users bug report
@api_view(["GET"])
@token_required
def my_bug_report(request, bug_report_id):
   
    report = BugReport.objects.get(bugreport_id=bug_report_id)

    if report.user != request.user:
        return Response({"error": "missing permissions, request denied"}, status=status.HTTP_403_FORBIDDEN)
    
    serializer = MyBugReportSerializer(instance=report)
    return Response({ "report" : serializer.data},status=200)

   

###########################################################################################################################


################################################## founderdashboard views #################################################


# get resolved bug reports
@api_view(["GET"])
@token_required
@founder_only
def resolved_bug_reports(request):
 
    reports = BugReport.objects.filter(status="RESOLVED").order_by('-created_at')   
    serializer = BugReportsSerializer(reports, many=True)
    
    return Response({ "reports" : serializer.data },status=200)


# get users id info
@api_view(["GET"])
@token_required
@founder_only
def resolved_bug_report(request, bug_report_id):
   
    report = BugReport.objects.get(bugreport_id=bug_report_id)
    serializer = ResolvedBugReportSerializer(instance=report)
    
    return Response({ "report" : serializer.data},status=200)


# get unresolved bug reports
@api_view(["GET"])
@token_required
@founder_only
def unresolved_bug_reports(request):
    reports = BugReport.objects.exclude(status="RESOLVED").order_by('-created_at')
    serializer = BugReportsSerializer(reports, many=True)
    
    return Response({ "reports" : serializer.data },status=200)


# get users id info
@api_view(["GET"])
@token_required
@founder_only
def unresolved_bug_report(request, bug_report_id):
   
    report = BugReport.objects.get(bugreport_id=bug_report_id)
    serializer = UnresolvedBugReportSerializer(instance=report)
    
    return Response({ "report" : serializer.data},status=200)


# change bug report status
@api_view(["POST"])
@token_required
@founder_only
def update_bug_report_status(request, bug_report_id):
   
    bug_report = get_object_or_404(BugReport, bugreport_id=bug_report_id)
    serializer = UpdateBugReportStatusSerializer(bug_report, data=request.data)
   
    if serializer.is_valid():
        serializer.save()
      
        return Response({ "message" : "bug report status successfully changed"}, status=200)
  
    else:
        return Response({ "error" : serializer.errors }, status=status.HTTP_400_BAD_REQUEST)
    

###########################################################################################################################
