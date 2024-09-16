# rest framework
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

# models
from .models import Transcript

# serializers
from users.serializers.students.students_serializers import StudentSourceAccountSerializer


class TranscriptCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Transcript
        fields = ['student', 'score', 'comment']

    def __init__(self, *args, **kwargs):
        super(TranscriptCreationSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]
        self.fields['comment'].required = False


class TranscriptFormSerializer(serializers.ModelSerializer):

    student = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()
    comment = serializers.SerializerMethodField()

    class Meta:
        model = Transcript
        fields = ['student', 'score', 'comment']

    def get_student(self, obj):
        return StudentSourceAccountSerializer(obj.student).data if obj.student else None

    def get_score(self, obj):
        return obj.score if obj.score else None

    def get_comment(self, obj):
        return obj.comment if obj.comment else None
