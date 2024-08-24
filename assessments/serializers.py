# python 

# django

# rest framework
from rest_framework import serializers

# models
from .models import Assessment
from classes.models import Classroom

# serializers


class AssessmentCreationSerializer(serializers.ModelSerializer):

    classroom = serializers.PrimaryKeyRelatedField(queryset=Classroom.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Assessment
        fields = ['unique_identifier', 'title', 'assessment_type', 'total', 'percentage_towards_term_mark', 'due_date', 'term', 'classroom', 'set_by', 'subject', 'grade', 'school']