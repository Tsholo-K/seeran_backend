# python 

# django

# rest framework
from rest_framework import serializers

# models
from .models import Assessment
from classes.models import Classroom

# serializers
from users.serializers import BySerializer


class AssessmentCreationSerializer(serializers.ModelSerializer):

    classroom = serializers.PrimaryKeyRelatedField(queryset=Classroom.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Assessment
        fields = ['title', 'set_by', 'total', 'percentage_towards_term_mark', 'term', 'classroom', 'subject', 'grade', 'school', 'due_date', 'unique_identifier', 'assessment_type']