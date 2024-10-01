# rest framework
from rest_framework import serializers

# models
from .models import EmailAddressBan


# users email bans serializer   
class EmailBansSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmailAddressBan
        fields = ['is_ban_appealable', 'appeal_status', 'timestamp', 'email_address_ban_id']


# users email ban
class EmailBanSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmailAddressBan
        fields = ['is_ban_appealable', 'banned_email_address', 'reason_for_ban', 'appeal_status', 'otp_send', 'timestamp', 'email_address_ban_id']
 

# users email ban
class AppealEmailBanSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmailAddressBan
        fields = ['appeal']
        