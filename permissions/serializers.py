# rest framework
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

# models
from .models import Assessment
from users.models import BaseUser
from classrooms.models import Classroom

# serializers
from users.serializers.general_serializers import SourceAccountSerializer, BasicAccountDetailsEmailSerializer
from users.serializers.students.students_serializers import StudentBasicAccountDetailsEmailSerializer
from topics.serializers import TopicSerializer


class AssessmentCreationSerializer(serializers.ModelSerializer):

    classroom = serializers.PrimaryKeyRelatedField(queryset=Classroom.objects.all(), required=False, allow_null=True)
    assessor = serializers.PrimaryKeyRelatedField(queryset=BaseUser.objects.all(), required=False, allow_null=True),
    moderator = serializers.PrimaryKeyRelatedField(queryset=BaseUser.objects.all(), required=False, allow_null=True),
    percentage_towards_term_mark = serializers.DecimalField(required=False, max_digits=5, decimal_places=2)

    class Meta:
        model = Assessment
        fields = ['assessor', 'title', 'assessment_type', 'total', 'percentage_towards_term_mark', 'start_time', 'dead_line', 'term', 'classroom', 'subject', 'grade', 'school', 'moderator']

    def __init__(self, *args, **kwargs):
        super(AssessmentCreationSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]

