# python 
import datetime

# rest framework
from rest_framework import serializers

# models
from .models import EmailBan



### email ban/appeals serilizers ###


# email ban
class EmailBanSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = EmailBan
        fields = [ 'email', 'reason', 'can_appeal', 'ban_id' ]


# email ban appeal
class EmailBanAppealsSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmailBan
        fields = [ 'email', 'reason', 'status', 'appeal_id' ]

        
