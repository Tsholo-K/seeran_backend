# rest framework
from rest_framework import serializers

# models
from .models import StudentSubjectPerformance


class StudentPerformanceSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentSubjectPerformance
        fields = ['pass_rate', 'highest_score', 'lowest_score', 'average_score', 'median_score', 'completion_rate', 'mode_score', 'passed']


