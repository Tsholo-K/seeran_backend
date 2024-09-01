# rest framework
from rest_framework import serializers

# models
from .models import DailySchedule


# schedule days
class DailyScheduleSerializer(serializers.ModelSerializer):
    
    day = serializers.SerializerMethodField()

    class Meta:
        model = DailySchedule
        fields = [ 'day_of_week', 'daily_schedule_id' ]
        
    def get_day(self, obj):
        return obj.day.title()

