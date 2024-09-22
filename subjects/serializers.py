# django
from django.utils.translation import gettext_lazy as _

# rest framework
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

# models
from grades.models import Grade
from .models import Subject

# serializers
from classrooms.serializers import ClassesSerializer


class SubjectCreationSerializer(serializers.ModelSerializer):
    
    # explicitly declaring the field since its set as editable=False in the model, 
    # specifying that a field should not be included in forms autogenerated from the model. This includes the admin site and serializers in Django Rest Framework
    grade = serializers.PrimaryKeyRelatedField(queryset=Grade.objects.all()) 

    class Meta:
        model = Subject
        fields = ['subject', 'major_subject', 'pass_mark', 'grade']

    def __init__(self, *args, **kwargs):
        super(SubjectCreationSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]


class UpdateSubjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subject
        fields = ['major_subject', 'pass_mark']

    def __init__(self, *args, **kwargs):
        super(UpdateSubjectSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]
        # Set all fields to be optional by making them not required
        for field in self.fields:
            self.fields[field].required = False


class SubjectsSerializer(serializers.ModelSerializer):
    
    subject = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [ 'subject', 'subject_id', 'classroom_count', 'teacher_count', 'student_count' ]

    def get_subject(self, obj):
        return obj.subject.title()


class SubjectSerializer(serializers.ModelSerializer):

    classrooms = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ['classrooms']
    
    def get_classrooms(self, obj):
        return ClassesSerializer(obj.classrooms.all(), many=True).data


class SubjectDetailsSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Subject
        fields = ['classroom_count', 'teacher_count', 'student_count', 'major_subject', 'pass_mark']
