# python 

# django
from django.core.cache import cache

# rest framework
from rest_framework import serializers

# models
from .models import Classroom
from users.models import CustomUser

# serilializers
from users.serializers import AccountSerializer


class ClassSerializer(serializers.ModelSerializer):

    teacher = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ['classroom_identifier', 'teacher', 'students', 'student_count', 'group', 'subject']

    def get_teacher(self, obj):
        if obj.teacher:
            return f'{obj.teacher.surname} {obj.teacher.name}'.title()
        else:
            return None

    def get_students(self, obj):
        students = obj.students.all()
        serializer = AccountSerializer(students, many=True)
        return serializer.data
    
    def get_student_count(self, obj):
        return obj.students.count()
    

class ClassUpdateSerializer(serializers.ModelSerializer):

    teacher = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False, allow_null=True)
    classroom_identifier = serializers.CharField(required=False)
    group = serializers.CharField(required=False)

    class Meta:
        model = Classroom
        fields = ['classroom_identifier', 'teacher', 'group']


class TeacherClassesSerializer(serializers.ModelSerializer):

    subject = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
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
        model = Classroom
        fields = ['classroom_identifier', 'student_count', 'group', 'id']

    def get_student_count(self, obj):
        return obj.students.count()
    
    def get_id(self, obj):
        return obj.class_id