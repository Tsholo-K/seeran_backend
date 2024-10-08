# rest framework
from rest_framework import serializers

# models
from .models import StudentSubjectPerformance

# serializers
from assessments.serializers import GradedAssessmentsSerializer


class StudentPerformanceSerializer(serializers.ModelSerializer):

    assessments = serializers.SerializerMethodField()

    class Meta:
        model = StudentSubjectPerformance
        fields = ['pass_rate', 'highest_score', 'lowest_score', 'average_score', 'median_score', 'completion_rate', 'mode_score', 'passed', 'assessments']

    def get_assessments(self, obj):
        return GradedAssessmentsSerializer(obj.subject.assessments.filter(term=obj.term, grade=obj.grade, formal=True)).data if obj.subject else None



