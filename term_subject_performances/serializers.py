# rest framework
from rest_framework import serializers

# models
from .models import TermSubjectPerformance

# serializers
from accounts.serializers.students.serializers import StudentBasicAccountDetailsEmailSerializer


class TermSubjectPerformanceSerializer(serializers.ModelSerializer):

    top_performers = StudentBasicAccountDetailsEmailSerializer(many=True)
    students_failing_the_subject_in_the_term = StudentBasicAccountDetailsEmailSerializer(many=True)

    class Meta:
        model = TermSubjectPerformance
        fields = ['pass_rate', 'highest_score', 'lowest_score', 'average_score', 'median_score', 'standard_deviation', 'percentile_distribution', 'completion_rate', 'top_performers', 'students_failing_the_subject_in_the_term', 'improvement_rate']


