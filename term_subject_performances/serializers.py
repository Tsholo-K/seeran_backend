# rest framework
from rest_framework import serializers

# models
from .models import TermSubjectPerformance

# serializers
from users.serializers.students.students_serializers import LeastAccountDetailsSerializer


class TermSubjectPerformanceSerializer(serializers.ModelSerializer):

    top_performers = serializers.SerializerMethodField()
    students_failing_the_subject_in_the_term = serializers.SerializerMethodField()

    class Meta:
        model = TermSubjectPerformance
        fields = ['pass_rate', 'highest_score', 'lowest_score', 'average_score', 'median_score', 'standard_deviation', 'percentile_distribution', 'completion_rate', 'top_performers', 'students_failing_the_subject_in_the_term', 'improvement_rate']

    def get_top_performers(self, obj):
        return LeastAccountDetailsSerializer(obj.top_performers.all(), many=True)

    def get_students_failing_the_subject_in_the_term(self, obj):
        return LeastAccountDetailsSerializer(obj.students_failing_the_subject_in_the_term.all(), many=True)


