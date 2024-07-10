# python 

# rest framework
from rest_framework import serializers

# models
from .models import EmailBan


### email ban serilizers ###


# users email bans serializer   
class EmailBansSerializer(serializers.ModelSerializer):
    
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = EmailBan
        fields = [ 'can_appeal', 'ban_id', 'banned_at', 'status' ]
        
    def get_status(self, obj):
        return obj.status.title()


# users email ban
class EmailBanSerializer(serializers.ModelSerializer):
    
    status = serializers.SerializerMethodField()

    class Meta:
        model = EmailBan
        fields = [ 'can_appeal', 'email', 'banned_at', 'reason', 'ban_id', 'status', 'otp_send' ]
        
    def get_status(self, obj):
        return obj.status.title()
 

# users email ban
class AppealEmailBanSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmailBan
        fields = [ 'appeal' ]
        