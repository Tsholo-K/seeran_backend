# rest framework
from rest_framework import serializers

# models
from accounts.models import Founder


class FounderAccountDetailsSerializer(serializers.ModelSerializer):

    image = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()

    class Meta:
        model = Founder
        fields = ['name', 'surname', 'role', 'image', 'identifier', 'account_id']
            
    def get_image(self, obj):
        return obj.profile_picture.url if obj.profile_picture else '/default-user-icon.svg'
    
    def get_identifier(self, obj):
        return obj.email_address


class FounderSecurityInformationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Founder
        fields = ['multifactor_authentication']

