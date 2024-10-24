# rest framework
from rest_framework import serializers

# django
from django.core.cache import cache

# models
from accounts.models import Principal

# utility functions 
from accounts import utils as accounts_utilities


class PrincipalAccountCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Principal
        fields = ['name', 'surname', 'contact_number', 'email_address', 'school', 'role']
        

class UpdatePrincipalAccountSerializer(serializers.ModelSerializer):

    class Meta:
        model = Principal
        fields = ['name', 'surname', 'email_address', 'contact_number']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields optional 
        for field in self.fields:
            self.fields[field].required = False

class PrincipalSecurityInformationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Principal
        fields = [ 'multifactor_authentication']


class PrincipalAccountSerializer(serializers.ModelSerializer):
    
    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Principal
        fields = ['name', 'surname', 'identifier', 'account_id', 'image']
    
    def get_name(self, obj):
        """Return the formatted name of the user."""
        return obj.name.title()

    def get_surname(self, obj):
        """Return the formatted surname of the user."""
        return obj.surname.title()

    def get_identifier(self, obj):
        """Return the identifier for the user: email."""
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


class PrincipalAccountSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Principal
        fields = ['name', 'surname', 'identifier', 'image', 'account_id']
    
    def get_name(self, obj):
        return obj.name.title()
    
    def get_surname(self, obj):
        return obj.surname.title()

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


class PrincipalAccountDetailsSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = Principal
        fields = ['name', 'surname', 'identifier', 'contact_number', 'image', 'role', 'account_id']
    
    def get_name(self, obj):
        return obj.name.title()
    
    def get_surname(self, obj):
        return obj.surname.title()
        
    def get_role(self, obj):
        return obj.role.title()

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


