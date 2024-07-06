# python 

# rest framework
from rest_framework import serializers

# django
from django.core.cache import cache

# models
from .models import BugReport


### users balance serilizers ###


# create bug report seralizer
class CreateBugReportSerializer(serializers.ModelSerializer):

    class Meta:
        model = BugReport
        fields = [ 'user', 'section', 'description', 'dashboard' ]
        
        
class UpdateBugReportStatusSerializer(serializers.ModelSerializer):

    class Meta:
        model = BugReport
        fields = [ 'status' ]
        
        
class BugReportsSerializer(serializers.ModelSerializer):

    status = serializers.SerializerMethodField()
    
    class Meta:
        model = BugReport
        fields = [ 'dashboard', 'created_at', 'updated_at', 'status', 'bugreport_id' ]
        
    def get_status(self, obj):
        return obj.status.replace("_", " ").title()
        
        
class BugReportSerializer(serializers.ModelSerializer):
    
    user = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = BugReport
        fields = [ 'section', 'created_at', 'updated_at', 'status', 'description', 'dashboard', 'user' ]
        
    def get_status(self, obj):
        return obj.status.replace("_", " ").title()
    
    def get_user(self, obj):
        user = obj.user

        if user is not None:
            return {
                'name': user.name,
                'surname': user.surname,
                'email': user.email,
                'picture': user.profile_picture.url if user.profile_picture else None,
                'id' : user.account_id,
            }
        
        else:
            return None
        
