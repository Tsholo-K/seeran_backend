from rest_framework import serializers
from .models import School

class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ['name', 'email', 'contact_number', 'school_type', 'province', 'school_district', 'school_id']
