# rest framework
from rest_framework import serializers

# models
from .models import EmailBan


# users email bans serializer   
class EmailBansSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmailBan
        fields = ['can_appeal', 'ban_id', 'banned_at', 'status']


# users email ban
class EmailBanSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmailBan
        fields = ['can_appeal', 'email', 'banned_at', 'reason', 'ban_id', 'status', 'otp_send']
 

# users email ban
class AppealEmailBanSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmailBan
        fields = ['appeal']
        