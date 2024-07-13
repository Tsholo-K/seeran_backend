# python 
from decouple import config

# django
from django.core.cache import cache

# rest framework
from rest_framework import serializers

# models
from .models import Grade


class GradesSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Grade
        fields = [ 'grade' ]
