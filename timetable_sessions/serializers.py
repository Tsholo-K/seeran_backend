# rest framework
from rest_framework import serializers

# models
from .models import TimetableSession


class SessoinsSerializer(serializers.ModelSerializer):
    
    session_from = serializers.TimeField(format='%H:%M')
    session_till = serializers.TimeField(format='%H:%M')

    class Meta:
        model = TimetableSession
        fields = [ 'type', 'classroom', 'session_from', 'session_till' ]

