# rest framework
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

# models
from .models import AssessmentTranscript

# serializers
from accounts.serializers.students.serializers import StudentSourceAccountSerializer, LeastAccountDetailsSerializer, StudentBasicAccountDetailsEmailSerializer


class TranscriptUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = AssessmentTranscript
        fields = ['score', 'comment']

    def __init__(self, *args, **kwargs):
        super(TranscriptUpdateSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]
        for field in self.fields:
            self.fields[field].required = False


class TranscriptFormSerializer(serializers.ModelSerializer):

    student = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentTranscript
        fields = ['student', 'score', 'comment', 'total']

    def get_student(self, obj):
        return StudentSourceAccountSerializer(obj.student).data

    def get_total(self, obj):
        return obj.assessment.total


class TranscriptsSerializer(serializers.ModelSerializer):

    student = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentTranscript
        fields = ['student', 'percent_score', 'transcript_id']

    def get_student(self, obj):
        return LeastAccountDetailsSerializer(obj.student).data


class TranscriptSerializer(serializers.ModelSerializer):

    student = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentTranscript
        fields = ['student', 'score', 'comment', 'total']

    def get_student(self, obj):
        return StudentBasicAccountDetailsEmailSerializer(obj.student).data

    def get_total(self, obj):
        return str(obj.assessment.total)
