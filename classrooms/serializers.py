# rest framework
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

# models
from .models import Classroom

# serilializers
from accounts.serializers.teachers.serializers import TeacherAccountSerializer, TeacherFullNameSerializer, TeacherBasicAccountDetailsEmailSerializer
from accounts.serializers.students.serializers import StudentSourceAccountSerializer


class ClassroomCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Classroom
        fields = ['classroom_number', 'group', 'teacher', 'register_classroom', 'subject', 'grade', 'school']
    
    def __init__(self, *args, **kwargs):
        super(ClassroomCreationSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]
        # Make some fields optional
        self.fields['teacher'].required = False
        self.fields['subject'].required = False

class UpdateClassroomSerializer(serializers.ModelSerializer):

    class Meta:
        model = Classroom
        fields = [ 'classroom_number', 'group']
    
    def __init__(self, *args, **kwargs):
        super(UpdateClassroomSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]
        for field in self.fields:
            self.fields[field].required = False

class ClassroomSerializer(serializers.ModelSerializer):

    teacher = serializers.SerializerMethodField()
    students = StudentSourceAccountSerializer(many=True)
    subject = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ['classroom_number', 'group', 'subject', 'student_count', 'students', 'teacher']

    def get_teacher(self, obj):
        if obj.teacher:
            return TeacherAccountSerializer(obj.teacher).data
        return None

    def get_subject(self, obj):
        return obj.subject.subject if obj.subject else None

class StudentClassroomSerializer(serializers.ModelSerializer):

    teacher = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ['classroom_number', 'group', 'grade', 'subject', 'student_count', 'teacher']

    def get_teacher(self, obj):
        if obj.teacher:
            return TeacherAccountSerializer(obj.teacher).data
        return None

    def get_subject(self, obj):
        return obj.subject.subject if obj.subject else None

    def get_grade(self, obj):
        return obj.grade.grade


class ClassroomDetailsSerializer(serializers.ModelSerializer):

    teacher = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ['classroom_number', 'group', 'student_count', 'teacher']

    def get_teacher(self, obj):
        if obj.teacher:
            return TeacherBasicAccountDetailsEmailSerializer(obj.teacher).data
        return None


class ClassesSerializer(serializers.ModelSerializer):

    teacher = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ['teacher', 'classroom_number', 'student_count', 'group', 'classroom_id']

    def get_teacher(self, obj):
        if obj.teacher:
            return TeacherFullNameSerializer(obj.teacher).data
        else:
            return None


class ClassroomsSerializer(serializers.ModelSerializer):

    subject = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ['classroom_number', 'subject', 'grade', 'student_count', 'group', 'classroom_id']

    def get_subject(self, obj):
        return obj.subject.subject if obj.subject else None

    def get_grade(self, obj):
        return obj.grade.grade


class TeacherRegisterClassSerializer(serializers.ModelSerializer):

    class Meta:
        model = Classroom
        fields = ['classroom_number', 'student_count', 'group', 'classroom_id']
