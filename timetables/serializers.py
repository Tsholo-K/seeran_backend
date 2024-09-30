# rest framework
from rest_framework import serializers

# models
from .models import Timetable


# schedule days
class TimetableSerializer(serializers.ModelSerializer):
    
    day = serializers.SerializerMethodField()

    class Meta:
        model = Timetable
        fields = [ 'day_of_week', 'timetables_id' ]
        
    def get_day(self, obj):
        return obj.day.title()

