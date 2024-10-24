# rest framework
from rest_framework import serializers

# django
from django.core.cache import cache

# models
from accounts.models import Parent

# utility functions 
from accounts import utils as accounts_utilities


class ParentAccountCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Parent
        fields = ['name', 'surname', 'email_address', 'role']

    def __init__(self, *args, **kwargs):
        super(ParentAccountCreationSerializer, self).__init__(*args, **kwargs)
        # remove email validation
        self.fields['email_address'].validators = []


class ParentAccountUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Parent
        fields = ['name', 'surname', 'email_address']

    def __init__(self, *args, **kwargs):
        super(ParentAccountUpdateSerializer, self).__init__(*args, **kwargs)
        # Make all fields optional 
        for field in self.fields:
            self.fields[field].required = False
        self.fields['email_address'].validators = []


class ParentSecurityInformationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Parent
        fields = ['multifactor_authentication', 'event_emails']
    

class ParentAccountSerializer(serializers.ModelSerializer):
    
    identifier = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Parent
        fields = ['name', 'surname', 'identifier', 'image', 'account_id']

    def get_identifier(self, obj):
        """Return the identifier for the user: ID number, passport number, or email."""
        return obj.email_address

    def get_image(self, obj):
        existing_signed_url = cache.get(str(obj.account_id) + 'profile_picture')
        if existing_signed_url:
            return existing_signed_url

        if obj.profile_picture:
            singed_url = accounts_utilities.generate_signed_url(obj.profile_picture.name)
            cache.set(str(obj.account_id) + 'profile_picture', singed_url, timeout=3600) 

            return singed_url

        return '/default-user-icon.svg'
    

class ParentAccountDetailsSerializer(serializers.ModelSerializer):

    identifier = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Parent
        fields = ['name', 'surname', 'identifier', 'role', 'image', 'account_id']
    
    def get_identifier(self, obj):
        return obj.email_address

    def get_image(self, obj):
        existing_signed_url = cache.get(str(obj.account_id) + 'profile_picture')
        if existing_signed_url:
            return existing_signed_url

        if obj.profile_picture:
            singed_url = accounts_utilities.generate_signed_url(obj.profile_picture.name)
            cache.set(str(obj.account_id) + 'profile_picture', singed_url, timeout=3600) 

            return singed_url

        return '/default-user-icon.svg'
