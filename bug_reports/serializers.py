# python 

# rest framework
from rest_framework import serializers

# django

# models
from .models import BugReport

# serializers
from users.serializers import AccountSerializer


### users balance serilizers ###


# create bug report seralizer
class CreateBugReportSerializer(serializers.ModelSerializer):

    class Meta:
        model = BugReport
        fields = [ 'user', 'section', 'description', 'dashboard' ]


class MyBugReportSerializer(serializers.ModelSerializer):
    
    status = serializers.SerializerMethodField()

    class Meta:
        model = BugReport
        fields = [ 'section', 'created_at', 'updated_at', 'status', 'description' ]
        
    def get_status(self, obj):
        return obj.status.replace("_", " ").title()
     
        
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
        fields = [ 'section', 'created_at', 'updated_at',  'status', 'description', 'dashboard', 'user' ]
    
    def get_status(self, obj):
        return obj.status.replace("_", " ").title()
    
    def get_user(self, obj):
        if obj.user:
            return AccountSerializer(obj.user).data
        else:
            return None
