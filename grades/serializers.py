# python 
from decouple import config

# django
from django.core.cache import cache

# rest framework
from rest_framework import serializers

# models
from .models import Grade, Subject


class GradesSerializer(serializers.ModelSerializer):
    
    id = serializers.SerializerMethodField()

    class Meta:
        model = Grade
        fields = [ 'grade', 'id' ]

    def get_id(self, obj):
        return obj.grade_id


class GradeSerializer(serializers.ModelSerializer):
    
    subjects = serializers.SerializerMethodField()

    class Meta:
        model = Grade
        fields = [ 'grade', 'subjects' ]

    def get_subjects(self, obj):
        subjects = obj.grade_subjects.all()
        serializer = SubjectsSerializer(subjects, many=True)
        return serializer.data


class SubjectsSerializer(serializers.ModelSerializer):
    
    subject = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()
    teachers = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [ 'subject', 'subject_id', 'groups', 'teachers', 'students' ]

    def get_subject(self, obj):
        return obj.subject.title()

    def get_groups(self, obj):
        return obj.subject_classes.count()

    def get_teachers_count(self, obj):
        teachers = set()
        for classroom in obj.subject_classes.all():
            teachers.add(classroom.teacher.account_id)
        return len(teachers)

    def get_students_count(self, obj):
        students = set()
        for classroom in obj.subject_classes.all():
            for student in classroom.students.all():
                students.add(student.account_id)
        return len(students)
