# python 

# django

# rest framework
from rest_framework import serializers

# models
from grades.models import Grade, Subject
from classes.models import Classroom


class GradeCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Grade
        fields = ['grade', 'major_subjects', 'none_major_subjects', 'school']


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
        

class SubjectCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subject
        fields = ['grade', 'subject', 'major_subject', 'pass_mark']


class SubjectsSerializer(serializers.ModelSerializer):
    
    subject = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [ 'subject', 'subject_id', 'classes_count', 'teacher_count', 'student_count' ]

    def get_subject(self, obj):
        return obj.subject.title()


class SubjectDetailSerializer(serializers.ModelSerializer):

    classes = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ['classes']
    
    def get_classes(self, obj):
        return ClassesSerializer(obj.subject_classes.all(), many=True).data


class ClassesSerializer(serializers.ModelSerializer):

    teacher = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ['classroom_number', 'teacher', 'student_count', 'group', 'class_id']

    def get_teacher(self, obj):
        if obj.teacher:
            return f'{obj.teacher.surname} {obj.teacher.name}'.title()
        else:
            return None
