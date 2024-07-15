# python 

# django
from django.core.cache import cache

# rest framework
from rest_framework import serializers

# models
from .models import Classroom

# serilializers
from users.serializers import UsersSerializer


class ClassSerializer(serializers.ModelSerializer):

    teacher = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ['classroom_identifier', 'teacher', 'students', 'student_count','group']

    def get_teacher(self, obj):
        if obj.teacher:
            return f'{obj.teacher.surname} {obj.teacher.name}'.title()
        else:
            return None

    def get_students(self, obj):
        students = obj.students.all()
        serializer = UsersSerializer(students, many=True)
        return serializer.data
    
    def get_student_count(self, obj):
        return obj.students.count()