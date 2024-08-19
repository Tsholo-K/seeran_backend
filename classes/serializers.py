# python 

# django

# rest framework
from rest_framework import serializers

# models
from .models import Classroom
from users.models import CustomUser
from grades.models import Subject

# serilializers
from users.serializers import AccountSerializer


class ClassCreationSerializer(serializers.ModelSerializer):

    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), required=False, allow_null=True)
    teacher = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.filter(role='TEACHER'), required=False)

    class Meta:
        model = Classroom
        fields = ['classroom_number', 'group', 'subject', 'register_class', 'teacher', 'grade', 'school']
    
    def validate(self, data):
        """
        Ensure that the subject field is only required when register_class is False.
        """
        if not data.get('register_class') and not data.get('subject'):
            raise serializers.ValidationError({"error": "a subject is required for the classroom when 'register_class' is False"})
        return data

class ClassSerializer(serializers.ModelSerializer):

    teacher = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ['classroom_number', 'teacher', 'students', 'student_count', 'group', 'subject', 'grade']

    def get_teacher(self, obj):
        if obj.teacher:
            return f'{obj.teacher.surname} {obj.teacher.name}'.title()
        return None

    def get_students(self, obj):
        return AccountSerializer(obj.students.all(), many=True).data
            
    def get_subject(self, obj):
        if  obj.register_class:
            return 'Register Class'
        if obj.subject:
            return f'{obj.subject.subject}'.title()
        return None
            
    def get_grade(self, obj):
        return obj.grade.grade


class ClassUpdateSerializer(serializers.ModelSerializer):

    classroom_number = serializers.CharField(required=False)
    group = serializers.CharField(required=False)

    class Meta:
        model = Classroom
        fields = [ 'classroom_number', 'group']


class TeacherClassesSerializer(serializers.ModelSerializer):

    subject = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ['classroom_number', 'subject', 'grade', 'student_count', 'group', 'class_id']

    def get_subject(self, obj):
        if  obj.register_class:
            return 'Register Class'
        if obj.subject:
            return f'{obj.subject.subject}'.title()
        return None

    def get_grade(self, obj):
        return obj.grade.grade


class TeacherRegisterClassSerializer(serializers.ModelSerializer):

    class Meta:
        model = Classroom
        fields = ['classroom_number', 'student_count', 'group', 'class_id']
