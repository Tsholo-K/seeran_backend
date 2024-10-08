# rest framework
from rest_framework import serializers

# models
from .models import ClassroomPerformance

# serializers
from accounts.serializers.students.serializers import StudentBasicAccountDetailsEmailSerializer


class ClassroomPerformanceSerializer(serializers.ModelSerializer):

    top_performers = StudentBasicAccountDetailsEmailSerializer(many=True)
    students_failing_the_classroom = StudentBasicAccountDetailsEmailSerializer(many=True)

    class Meta:
        model = ClassroomPerformance
        fields = ['pass_rate', 'highest_score', 'lowest_score', 'average_score', 'median_score', 'standard_deviation', 'percentile_distribution', 'completion_rate', 'top_performers', 'students_failing_the_classroom', 'improvement_rate']


