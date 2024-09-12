# rest framework
from rest_framework import serializers

# models
from .models import Topic

# serializers


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ['name']