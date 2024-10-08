# rest framework
from rest_framework import serializers

# models
from .models import StudentSubjectPerformance
from student_subject_performances.models import StudentSubjectPerformance

# serializers
from assessments.serializers import GradedAssessmentsSerializer


class StudentPerformanceSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentSubjectPerformance
        fields = ['pass_rate', 'highest_score', 'lowest_score', 'average_score', 'median_score', 'completion_rate', 'mode_score', 'passed']



class StudentSubjectPerformanceSerializer(serializers.ModelSerializer):

    assessments = serializers.SerializerMethodField()

    class Meta:
        model = StudentSubjectPerformance
        fields = ['assessments']

    def get_assessments(self, obj):
        return GradedAssessmentsSerializer(obj.subject.assessments.filter(term=obj.term, grade=obj.grade, formal=True), many=True).data if obj.subject else None


