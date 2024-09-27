# rest framework
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

# models
from .models import Assessment
from users.models import BaseUser
from classrooms.models import Classroom

# serializers
from users.serializers.general_serializers import SourceAccountSerializer
from users.serializers.students.students_serializers import LeastAccountDetailsSerializer
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


class AssessmentUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Assessment
        fields = ['start_time', 'dead_line', 'title', 'total', 'percentage_towards_term_mark', 'term', 'moderator']

    def __init__(self, *args, **kwargs):
        super(AssessmentUpdateSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]
        # Make all fields optional 
        for field in self.fields:
            self.fields[field].required = False


class AssessmentUpdateFormDataSerializer(serializers.ModelSerializer):

    term = serializers.SerializerMethodField()
    topics = TopicSerializer(many=True)
    moderator = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = ['start_time', 'dead_line', 'title', 'total', 'topics', 'percentage_towards_term_mark', 'term', 'moderator']

    def get_title(self, obj):
        return obj.title.title()

    def get_term(self, obj):
        return str(obj.term.term_id)

    def get_moderator(self, obj):
        return SourceAccountSerializer(obj.moderator).data if obj.moderator else None


class DueAssessmentsSerializer(serializers.ModelSerializer):

    title = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = ['title', 'assessment_type', 'dead_line', 'formal', 'assessment_id']

    def get_title(self, obj):
        return obj.title.title()


class CollectedAssessmentsSerializer(serializers.ModelSerializer):

    title = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = ['title', 'assessment_type', 'date_collected', 'formal', 'assessment_id']

    def get_title(self, obj):
        return obj.title.title()


class GradedAssessmentsSerializer(serializers.ModelSerializer):

    title = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = ['title', 'assessment_type', 'date_grades_released', 'formal', 'assessment_id']

    def get_title(self, obj):
        return obj.title.title()


class DueAssessmentSerializer(serializers.ModelSerializer):

    title = serializers.SerializerMethodField()
    term = serializers.SerializerMethodField()
    assessment_type = serializers.CharField(source='get_assessment_type_display')
    topics = TopicSerializer(many=True)
    moderator = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = ['title', 'assessment_type', 'total', 'formal', 'percentage_towards_term_mark', 'start_time', 'dead_line', 'term', 'topics', 'moderator']

    def get_title(self, obj):
        return obj.title.title()

    def get_term(self, obj):
        return obj.term.term.title()

    def get_moderator(self, obj):
        return SourceAccountSerializer(obj.moderator).data if obj.moderator else None


class CollectedAssessmentSerializer(serializers.ModelSerializer):

    title = serializers.SerializerMethodField()
    term = serializers.SerializerMethodField()
    assessment_type = serializers.CharField(source='get_assessment_type_display')
    topics = TopicSerializer(many=True)
    moderator = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = ['title', 'assessment_type', 'total', 'formal', 'percentage_towards_term_mark', 'date_collected', 'term', 'topics', 'moderator']

    def get_title(self, obj):
        return obj.title.title()

    def get_term(self, obj):
        return obj.term.term.title()

    def get_moderator(self, obj):
        return SourceAccountSerializer(obj.moderator).data if obj.moderator else None


class GradedAssessmentSerializer(serializers.ModelSerializer):

    title = serializers.SerializerMethodField()
    term = serializers.SerializerMethodField()
    assessment_type = serializers.CharField(source='get_assessment_type_display')
    topics = TopicSerializer(many=True)
    moderator = serializers.SerializerMethodField()
    top_performers = serializers.SerializerMethodField()
    students_who_failed_the_assessment = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = ['title', 'assessment_type', 'total', 'formal', 'percentage_towards_term_mark', 'date_collected', 'date_grades_released', 'term', 'topics', 'pass_rate', 'highest_score', 'lowest_score', 'average_score', 'median_score', 'mode_score', 'standard_deviation', 'percentile_distribution', 'completion_rate', 'interquartile_range', 'top_performers', 'students_who_failed_the_assessment', 'moderator']

    def get_title(self, obj):
        return obj.title.title()

    def get_term(self, obj):
        return obj.term.term.title()
    
    def get_top_performers(self, obj):
        return LeastAccountDetailsSerializer(obj.top_performers, many=True).data

    def get_students_who_failed_the_assessment(self, obj):
        return LeastAccountDetailsSerializer(obj.students_who_failed_the_assessment, many=True).data
    
    def get_moderator(self, obj):
        return SourceAccountSerializer(obj.moderator).data if obj.moderator else None
