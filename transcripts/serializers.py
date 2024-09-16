# rest framework
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

# models
from .models import Transcript


class TranscriptCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Transcript
        fields = ['student', 'score', 'comment']

    def __init__(self, *args, **kwargs):
        super(TranscriptCreationSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]
        self.fields['comment'].required = False


