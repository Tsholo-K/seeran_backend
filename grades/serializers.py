# python 

# django
from django.utils.translation import gettext_lazy as _

# rest framework
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

# models
from .models import Grade, Term, Subject
from schools.models import School

# serializers
from classes.serializers import ClassesSerializer


                                                            # Grade


class GradeCreationSerializer(serializers.ModelSerializer):

    # explicitly declaring the field since its set as editable=False in the model, 
    # specifying that a field should not be included in forms autogenerated from the model. This includes the admin site and serializers in Django Rest Framework
    grade = serializers.CharField(max_length=4) 
    school = serializers.PrimaryKeyRelatedField(queryset=School.objects.all())

    class Meta:
        model = Grade
        fields = ['major_subjects', 'none_major_subjects', 'grade', 'school']


class UpdateGradeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Grade
        fields = ['major_subjects', 'none_major_subjects']

    def __init__(self, *args, **kwargs):
        super(UpdateGradeSerializer, self).__init__(*args, **kwargs)
        # Set all fields to be optional by making them not required
        for field in self.fields:
            self.fields[field].required = False


class GradesSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Grade
        fields = ['grade', 'grade_id']


class StudentGradesSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Grade
        fields = ['grade', 'grade_id', 'student_count']


class GradeSerializer(serializers.ModelSerializer):
    
    subjects = serializers.SerializerMethodField()

    class Meta:
        model = Grade
        fields = ['subjects']

    def get_subjects(self, obj):
        return SubjectsSerializer(obj.grade_subjects.all(), many=True).data


class GradeDetailsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Grade
        fields = ['major_subjects', 'none_major_subjects', 'student_count']


                                                            # Term


class TermCreationSerializer(serializers.ModelSerializer):
    
    # explicitly declaring the field since its set as editable=False in the model, 
    # specifying that a field should not be included in forms autogenerated from the model. This includes the admin site and serializers in Django Rest Framework
    term = serializers.CharField(max_length=16) 
    grade = serializers.PrimaryKeyRelatedField(queryset=Grade.objects.all()) 
    school = serializers.PrimaryKeyRelatedField(queryset=School.objects.all())

    class Meta:
        model = Term
        fields = ['term', 'weight', 'start_date', 'end_date', 'school_days', 'grade', 'school']

    def __init__(self, *args, **kwargs):
        super(TermCreationSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]


class UpdateTermSerializer(serializers.ModelSerializer):

    class Meta:
        model = Term
        fields = [ 'weight', 'start_date', 'end_date', 'school_days' ]

    def __init__(self, *args, **kwargs):
        super(UpdateTermSerializer, self).__init__(*args, **kwargs)
        # Set all fields to be optional by making them not required
        for field in self.fields:
            self.fields[field].required = False


class TermsSerializer(serializers.ModelSerializer):
            
    term = serializers.SerializerMethodField()

    class Meta:
        model = Term
        fields = ['term', 'weight', 'start_date', 'end_date', 'term_id']

    def get_term(self, obj):
        return obj.term.title()


class TermSerializer(serializers.ModelSerializer):
            
    term = serializers.SerializerMethodField()

    class Meta:
        model = Term
        fields = ['term', 'weight', 'start_date', 'end_date', 'school_days']
    
    def get_term(self, obj):
        return obj.term.title()


                                                            # Subject


class SubjectCreationSerializer(serializers.ModelSerializer):
    
    # explicitly declaring the field since its set as editable=False in the model, 
    # specifying that a field should not be included in forms autogenerated from the model. This includes the admin site and serializers in Django Rest Framework
    grade = serializers.PrimaryKeyRelatedField(queryset=Grade.objects.all()) 

    class Meta:
        model = Subject
        fields = ['subject', 'major_subject', 'pass_mark', 'grade']
    

class UpdateSubjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subject
        fields = ['major_subject', 'pass_mark']

    def __init__(self, *args, **kwargs):
        super(UpdateSubjectSerializer, self).__init__(*args, **kwargs)
        # Set all fields to be optional by making them not required
        for field in self.fields:
            self.fields[field].required = False


class SubjectsSerializer(serializers.ModelSerializer):
    
    subject = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [ 'subject', 'subject_id', 'classes_count', 'teacher_count', 'student_count' ]

    def get_subject(self, obj):
        return obj.subject.title()


class SubjectSerializer(serializers.ModelSerializer):

    classes = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ['classes']
    
    def get_classes(self, obj):
        return ClassesSerializer(obj.subject_classes.all(), many=True).data


class SubjectDetailsSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Subject
        fields = ['classes_count', 'teacher_count', 'student_count', 'major_subject', 'pass_mark']
