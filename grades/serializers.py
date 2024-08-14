# python 

# django

# rest framework
from rest_framework import serializers

# models
from ..grades.models import Grade, Subject
from classes.models import Classroom


class GradesSerializer(serializers.ModelSerializer):
    
    id = serializers.SerializerMethodField()

    class Meta:
        model = Grade
        fields = [ 'grade', 'id' ]

    def get_id(self, obj):
        return str(obj.grade_id)


class GradeSerializer(serializers.ModelSerializer):
    
    subjects = serializers.SerializerMethodField()

    class Meta:
        model = Grade
        fields = [ 'subjects' ]

    def get_subjects(self, obj):
        return SubjectsSerializer(obj.grade_subjects.all(), many=True).data
        


class SubjectsSerializer(serializers.ModelSerializer):
    
    subject = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()
    teacher_count = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [ 'subject', 'subject_id', 'groups', 'teacher_count', 'student_count' ]

    def get_subject(self, obj):
        return obj.subject.title()

    def get_groups(self, obj):
        return obj.subject_classes.count()

    def get_teacher_count(self, obj):
        teachers = set()
        for classroom in obj.subject_classes.all():
            if classroom.teacher:
                teachers.add(classroom.teacher.account_id)
        return len(teachers)

    def get_student_count(self, obj):
        students = set()
        for classroom in obj.subject_classes.all():
            for student in classroom.students.all():
                students.add(student.account_id)
        return len(students)


class SubjectDetailSerializer(serializers.ModelSerializer):

    classes = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ['classes']
    
    def get_classes(self, obj):
        return ClassesSerializer(obj.subject_classes.all(), many=True).data


class ClassesSerializer(serializers.ModelSerializer):

    teacher = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ['classroom_identifier', 'teacher', 'student_count', 'group', 'id']

    def get_teacher(self, obj):
        if obj.teacher:
            return f'{obj.teacher.surname} {obj.teacher.name}'.title()
        else:
            return None

    def get_student_count(self, obj):
        return obj.students.count()
    
    def get_id(self, obj):
        return str(obj.class_id)
