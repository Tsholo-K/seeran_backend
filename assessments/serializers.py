# python 

# django

# rest framework
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

# models
from .models import Assessment
from users.models import BaseUser
from classes.models import Classroom

# serializers


class AssessmentCreationSerializer(serializers.ModelSerializer):

    classroom = serializers.PrimaryKeyRelatedField(queryset=Classroom.objects.all(), required=False, allow_null=True)
    assessor = serializers.PrimaryKeyRelatedField(queryset=BaseUser.objects.all(), required=False, allow_null=True),
    percentage_towards_term_mark = serializers.DecimalField(required=False, max_digits=5, decimal_places=2)

    class Meta:
        model = Assessment
        fields = ['assessor', 'due_date', 'title', 'unique_identifier', 'assessment_type', 'total', 'percentage_towards_term_mark', 'start_time', 'dead_line', 'term', 'classroom', 'subject', 'grade', 'school']

    def __init__(self, *args, **kwargs):
        super(AssessmentCreationSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]


class AssessmentUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Assessment
        fields = ['due_date', 'title', 'unique_identifier', 'assessment_type', 'total', 'percentage_towards_term_mark']

    def __init__(self, *args, **kwargs):
        super(AssessmentUpdateSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]
        # Make all fields optional 
        for field in self.fields:
            self.fields[field].required = False


class DueAssessmentsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Assessment
        fields = ['title', 'assessment_type', 'due_date', 'formal', 'assessment_id']


class CollectedAssessmentsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Assessment
        fields = ['title', 'assessment_type', 'date_collected', 'formal', 'assessment_id']


class DueAssessmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Assessment
        fields = ['title', 'assessment_type', 'total', 'formal', 'percentage_towards_term_mark', 'due_date', 'topics', 'assessment_id']


class CollectedAssessmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Assessment
        fields = ['title', 'assessment_type', 'date_collected', 'formal', 'assessment_id']