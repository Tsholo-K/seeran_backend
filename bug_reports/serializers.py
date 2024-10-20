# python 

# rest framework
from rest_framework import serializers

# django

# models
from .models import BugReport

# serializers
from accounts.serializers.general_serializers import SourceAccountSerializer



# create bug report seralizer
class BugReportCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = BugReport
        fields = [ 'reporter', 'section', 'description', 'dashboard' ]
     
        
class UpdateBugReportStatusSerializer(serializers.ModelSerializer):

    class Meta:
        model = BugReport
        fields = [ 'status' ]
        
        
class BugReportsSerializer(serializers.ModelSerializer):

    status = serializers.SerializerMethodField()
    dashboard = serializers.SerializerMethodField()

    class Meta:
        model = BugReport
        fields = [ 'dashboard', 'created_at', 'updated_at', 'status', 'bugreport_id' ]
        
    def get_status(self, obj):
        return obj.status.replace("_", " ").title()
    
    def get_dashboard(self, obj):
        return obj.dashboard.title()
        

class BugReportSerializer(serializers.ModelSerializer):

    status = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()

    class Meta:
        model = BugReport
        fields = [ 'section', 'created_at', 'updated_at',  'status', 'description', 'dashboard', 'reporter' ]
    
    def get_status(self, obj):
        return obj.status.replace("_", " ").title()
    
    def get_user(self, obj):
        if obj.user:
            return SourceAccountSerializer(obj.user).data
        else:
            return None


class MyBugReportSerializer(serializers.ModelSerializer):
    
    status = serializers.SerializerMethodField()

    class Meta:
        model = BugReport
        fields = [ 'section', 'created_at', 'updated_at', 'status', 'description' ]
        
    def get_status(self, obj):
        return obj.status.replace("_", " ").title()
