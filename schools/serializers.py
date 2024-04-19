from rest_framework import serializers

# models
from .models import School
from authentication.models import CustomUser


class SchoolSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = School
        fields = ['name', 'email', 'contact_number', 'school_type', 'province', 'school_district', 'school_id']

class SchoolsSerializer(serializers.ModelSerializer):
    
    learners = serializers.SerializerMethodField()
    parents = serializers.SerializerMethodField()
    number_of_classrooms = serializers.SerializerMethodField()
    
    class Meta:
        model = School
        fields = [
            'name',
            'learners',
            'parents',
            'number_of_classes',
        ]
        
    def get_learners(self, obj):
        return CustomUser.objects.filter(school=obj, role='STUDENT').count()

    def get_parents(self, obj):
        return CustomUser.objects.filter(school=obj, role='PARENT').count()
    
    def get_number_of_classes(self, obj):
        return [].count()