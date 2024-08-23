# python 

# django
from django.core.exceptions import ValidationError

# rest framework
from rest_framework import serializers

# models
from .models import Grade, Term, Subject

# serializers
from classes.serializers import ClassesSerializer


class GradeCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Grade
        fields = ['grade', 'major_subjects', 'none_major_subjects', 'school']


class GradesSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Grade
        fields = [ 'grade', 'grade_id' ]


class GradeSerializer(serializers.ModelSerializer):
    
    subjects = serializers.SerializerMethodField()

    class Meta:
        model = Grade
        fields = [ 'subjects' ]

    def get_subjects(self, obj):
        return SubjectsSerializer(obj.grade_subjects.all(), many=True).data


class TermCreationSerializer(serializers.ModelSerializer):
        
    class Meta:
        model = Term
        fields = [ "term", 'weight', 'start_date', 'end_date', 'school_days', 'school', 'grade' ]
    

class UpdateSchoolTermSerializer(serializers.ModelSerializer):

    class Meta:
        model = Term
        fields = [ 'weight', 'start_date', 'end_date', 'school_days' ]

    def __init__(self, *args, **kwargs):
        super(UpdateSchoolTermSerializer, self).__init__(*args, **kwargs)
        # Set all fields to be optional by making them not required
        for field in self.fields:
            self.fields[field].required = False


class TermsSerializer(serializers.ModelSerializer):
        
    class Meta:
        model = Term
        fields = [ "term", 'weight', 'start_date', 'end_date', 'term_id' ]


class TermSerializer(serializers.ModelSerializer):
        
    class Meta:
        model = Term
        fields = [ "term", 'weight', 'start_date', 'end_date', 'school_days' ]


class SubjectCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subject
        fields = ['grade', 'subject', 'major_subject', 'pass_mark']


class SubjectsSerializer(serializers.ModelSerializer):
    
    subject = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [ 'subject', 'subject_id', 'classes_count', 'teacher_count', 'student_count' ]

    def get_subject(self, obj):
        return obj.subject.title()


class SubjectDetailSerializer(serializers.ModelSerializer):

    classes = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ['classes']
    
    def get_classes(self, obj):
        return ClassesSerializer(obj.subject_classes.all(), many=True).data

