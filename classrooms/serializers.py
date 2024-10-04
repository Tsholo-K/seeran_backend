# rest framework
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

# models
from .models import Classroom
from accounts.models import Teacher
from schools.models import School
from grades.models import Grade
from subjects.models import Subject

# serilializers
from accounts.serializers.students.serializers import StudentSourceAccountSerializer


class ClassCreationSerializer(serializers.ModelSerializer):

    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), required=False, allow_null=True)
    register_classroom = serializers.BooleanField(required=False)

    class Meta:
        model = Classroom
        fields = ['classroom_number', 'group', 'subject', 'register_classroom', 'teacher', 'grade', 'school']
    
    def __init__(self, *args, **kwargs):
        super(ClassCreationSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]
        self.fields['teacher'].required = False

class UpdateClassSerializer(serializers.ModelSerializer):

    classroom_number = serializers.CharField(required=False)
    group = serializers.CharField(required=False)

    class Meta:
        model = Classroom
        fields = [ 'classroom_number', 'group']
    
    def __init__(self, *args, **kwargs):
        super(UpdateClassSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]


class ClassroomSerializer(serializers.ModelSerializer):

    teacher = serializers.SerializerMethodField()
    students = StudentSourceAccountSerializer(many=True)
    subject = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ['classroom_number', 'group', 'subject', 'student_count', 'students', 'teacher', 'grade']

    def get_teacher(self, obj):
        if obj.teacher:
            return f'{obj.teacher.surname} {obj.teacher.name}'.title()
        return None
            
    def get_subject(self, obj):
        if  obj.register_class:
            return 'Register Class'
        if obj.subject:
            return f'{obj.subject.subject}'.title()
        return None
            
    def get_grade(self, obj):
        return obj.grade.grade



class ClassesSerializer(serializers.ModelSerializer):

    teacher = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ['teacher', 'classroom_number', 'student_count', 'group', 'classroom_id']

    def get_teacher(self, obj):
        if obj.teacher:
            return f'{obj.teacher.surname} {obj.teacher.name}'.title()
        else:
            return None


class TeacherClassroomsSerializer(serializers.ModelSerializer):

    subject = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ['classroom_number', 'subject', 'grade', 'student_count', 'group', 'classroom_id']

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
        fields = ['classroom_number', 'student_count', 'group', 'classroom_id']
