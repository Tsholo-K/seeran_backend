from rest_framework import serializers

# models
from .models import School
from authentication.models import CustomUser


class SchoolSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = School
        fields = ['name', 'email', 'contact_number', 'school_type', 'province', 'school_district', 'school_id']

class SchoolsSerializer(serializers.ModelSerializer):
    
    name = serializers.SerializerMethodField()
    learners = serializers.IntegerField()
    parents = serializers.IntegerField()
    number_of_classes = serializers.SerializerMethodField()
    
    class Meta:
        model = School
        fields = [
            'name',
            'learners',
            'parents',
            'number_of_classes',
        ]
        
    def get_name(self, obj):
        return obj.name.title()
    
    def get_number_of_classes(self, obj):
        return ['']