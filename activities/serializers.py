# python 

# django

# rest framework
from rest_framework import serializers

# models
from .models import Activity
from users.models import CustomUser

# serilializers
from users.serializers import AccountSerializer


class ActivityCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Activity
        fields = ['offence', 'details', 'logger', 'recipient', 'school']


class ActivitySerializer(serializers.ModelSerializer):

    logger = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ['offence', 'details', 'logger', 'school']

    def get_logger(self, obj):
        if  obj.register_class:
            return 'Register Class'
        
        if obj.subject:
            return f'{obj.subject}'.title()
        
        return None


class ActivitiesSerializer(serializers.ModelSerializer):

    id = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ['offence', 'date_logged', 'id']

    def get_id(self, obj):
        return  obj.activity_id


class ClassUpdateSerializer(serializers.ModelSerializer):

    teacher = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False, allow_null=True)
    classroom_identifier = serializers.CharField(required=False)
    group = serializers.CharField(required=False)

    class Meta:
        model = Activity
        fields = ['classroom_identifier', 'teacher', 'group']


class TeacherClassesSerializer(serializers.ModelSerializer):

    logger = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ['classroom_identifier', 'subject', 'grade', 'student_count', 'group', 'id']

    def get_subject(self, obj):
        if  obj.register_class:
            return 'Register Class'
        
        if obj.subject:
            return f'{obj.subject}'.title()
        
        return None

    def get_grade(self, obj):
        return obj.grade.grade
    
    def get_student_count(self, obj):
        return obj.students.count()
    
    def get_id(self, obj):
        return obj.class_id


class TeacherRegisterClassSerializer(serializers.ModelSerializer):

    student_count = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ['classroom_identifier', 'student_count', 'group', 'id']

    def get_student_count(self, obj):
        return obj.students.count()
    
    def get_id(self, obj):
        return obj.class_id