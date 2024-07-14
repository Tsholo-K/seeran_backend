# python 
from decouple import config

# django
from django.core.cache import cache

# rest framework
from rest_framework import serializers

# models
from .models import Grade, Subject


class GradesSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Grade
        fields = [ 'grade' ]


class GradeSerializer(serializers.ModelSerializer):
    
    subjects = serializers.SerializerMethodField()

    class Meta:
        model = Grade
        fields = [ 'subjects' ]

    def get_subjects(self, obj):
        if hasattr(obj, 'grade_subjects'):
            subjects = obj.grade_subjects.all()
            serializer = SubjectsSerializer(subjects, many=True)

            return serializer.data
        else:
            return []



class SubjectsSerializer(serializers.ModelSerializer):
    
    subject = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [ 'subject' ]

    def get_subject(self, obj):
        return obj.subject.title()