# python 

# django

# rest framework
from rest_framework import serializers

# models
from .models import Grade, Subject
from classes.models import Classroom


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

    def get_teachers(self, obj):
        teachers = set()
        for classroom in obj.subject_classes.all():
            teachers.add(classroom.teacher.account_id)
        return len(teachers)

    def get_students(self, obj):
        students = set()
        for classroom in obj.subject_classes.all():
            for student in classroom.students.all():
                students.add(student.account_id)
        return len(students)


class SubjectDetailSerializer(serializers.ModelSerializer):

    grade = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    classes = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [ 'grade', 'subject', 'classes']
    
    def get_grade(self, obj):
        return obj.grade.grade

    # def get_subject(self, obj):
    #     return obj.subject.title()
    
    def get_classes(self, obj):
        classes = obj.subject_classes.all()
        serializer = ClassSerializer(classes, many=True)
        return serializer.data


class ClassSerializer(serializers.ModelSerializer):

    teacher = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ['room_number', 'teacher', 'students', 'group']

    def get_teacher(self, obj):
        return obj.teacher.surname.title() + ' ' + obj.teacher.name.title()

    def get_students(self, obj):
        return obj.students.count()
