# rest framework
from rest_framework import serializers

# django
from django.core.cache import cache

# models
from accounts.models import Founder

# utility functions 
from accounts import utils as accounts_utilities


class FounderAccountDetailsSerializer(serializers.ModelSerializer):

    image = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()

    class Meta:
        model = Founder
        fields = ['name', 'surname', 'role', 'image', 'identifier', 'account_id']

    def get_image(self, obj):
        existing_signed_url = cache.get(str(obj.account_id) + 'profile_picture')
        if existing_signed_url:
            return existing_signed_url

        if obj.profile_picture:
            singed_url = accounts_utilities.generate_signed_url(obj.profile_picture.name)
            cache.set(str(obj.account_id) + 'profile_picture', singed_url, timeout=3600) 

            return singed_url

        return '/default-user-icon.svg'
    
    def get_identifier(self, obj):
        return obj.email_address


class FounderSecurityInformationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Founder
        fields = ['multifactor_authentication']

