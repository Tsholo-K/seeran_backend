# rest framework
from rest_framework import serializers

# django
from django.core.cache import cache

# models
from accounts.models import Admin

# utility functions 
from accounts import utils as accounts_utilities


class AdminAccountCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Admin
        fields = ['name', 'surname', 'email_address', 'school', 'role']

    def __init__(self, *args, **kwargs):
        super(AdminAccountCreationSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.fields['email_address'].validators = []


class AdminAccountUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Admin
        fields = ['name', 'surname', 'email_address']

    def __init__(self, *args, **kwargs):
        super(AdminAccountUpdateSerializer, self).__init__(*args, **kwargs)
        self.fields['email_address'].validators = []
        # Make all fields optional 
        for field in self.fields:
            self.fields[field].required = False


class AdminSecurityInformationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Admin
        fields = ['multifactor_authentication']
    

class AdminAccountSerializer(serializers.ModelSerializer):
    
    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Admin
        fields = ['name', 'surname', 'identifier', 'image', 'account_id']
    
    def get_name(self, obj):
        """Return the formatted name of the user."""
        return obj.name.title()

    def get_surname(self, obj):
        """Return the formatted surname of the user."""
        return obj.surname.title()

    def get_image(self, obj):
        existing_signed_url = cache.get(str(obj.account_id) + 'profile_picture')
        if existing_signed_url:
            return existing_signed_url

        if obj.profile_picture:
            singed_url = accounts_utilities.generate_signed_url(obj.profile_picture.name)
            cache.set(str(obj.account_id) + 'profile_picture', singed_url, timeout=86400) 

            return singed_url

        return '/default-user-icon.svg'
    
    def get_identifier(self, obj):
        """Return the identifier for the user: ID number, passport number, or email."""
        return obj.email_address
    

class AdminAccountDetailsSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = Admin
        fields = ['name', 'surname', 'identifier', 'role', 'image', 'account_id']
    
    def get_name(self, obj):
        return obj.name.title()
    
    def get_surname(self, obj):
        return obj.surname.title()
    
    def get_identifier(self, obj):
        return obj.email_address
        
    def get_role(self, obj):
        return obj.role.title()

    def get_image(self, obj):
        existing_signed_url = cache.get(str(obj.account_id) + 'profile_picture')
        if existing_signed_url:
            return existing_signed_url

        if obj.profile_picture:
            singed_url = accounts_utilities.generate_signed_url(obj.profile_picture.name)
            cache.set(str(obj.account_id) + 'profile_picture', singed_url, timeout=86400) 

            return singed_url

        return '/default-user-icon.svg'

