# python 

# django
from django.core.cache import cache

# rest framework
from rest_framework import serializers

# models
from .models import Classroom


####################################### admindashboard serializer ############################################


# user security information
class ClassesSerializer(serializers.ModelSerializer):
    
    teacher = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = [ 'teacher', 'students', 'group', 'room_number', 'class_id' ]

    def get_teacher(self, obj):
        return obj.teacher.name.title() + ' ' + obj.teacher.surname.title()
    
    def get_students(self, obj):
        return obj.students.count()
