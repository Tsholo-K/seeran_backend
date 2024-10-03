# rest framework
from rest_framework import serializers

# models
from .models import Timetable


# schedule days
class TimetableSerializer(serializers.ModelSerializer):

    class Meta:
        model = Timetable
        fields = [ 'day_of_week', 'timetables_id' ]

