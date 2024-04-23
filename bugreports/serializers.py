# rest framework
from rest_framework import serializers

# models
from .models import BugReport


### users balance serilizers ###


# user profile information
class CreateBugReportSerializer(serializers.ModelSerializer):

    class Meta:
        model = BugReport
        fields = [ 'user', 'section', 'description' ]
        
        
class BugReportsSerializer(serializers.ModelSerializer):

    class Meta:
        model = BugReport
        fields = [ 'section', 'created_at', 'updated_at', 'status' ]