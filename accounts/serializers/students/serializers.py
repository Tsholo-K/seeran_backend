# rest framework
from rest_framework import serializers

# django
from django.core.cache import cache

# models
from accounts.models import Student

# utility functions 
from accounts import utils as accounts_utilities


class StudentAccountCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Student
        fields = ['name', 'surname', 'email_address', 'role', 'id_number', 'passport_number', 'grade', 'school']

    def __init__(self, *args, **kwargs):
        super(StudentAccountCreationSerializer, self).__init__(*args, **kwargs)
        # Make some fields optional
        for field in ['email_address', 'id_number', 'passport_number']:
            self.fields[field].required = False
            self.fields[field].validators = []


class StudentAccountUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Student
        fields = ['name', 'surname', 'email_address']

    def __init__(self, *args, **kwargs):
        super(StudentAccountUpdateSerializer, self).__init__(*args, **kwargs)
        # Make all fields optional 
        for field in self.fields:
            self.fields[field].required = False
        self.fields['email_address'].validators = []


class StudentSecurityInformationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Student
        fields = ['multifactor_authentication', 'event_emails']

    
class StudentSourceAccountSerializer(serializers.ModelSerializer):

    identifier = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ['name', 'surname', 'identifier', 'image', 'account_id']

    def get_identifier(self, obj):
        """Return the identifier for the user: ID number, passport number, or email."""
        return obj.id_number or obj.passport_number

    def get_image(self, obj):
        if obj.profile_picture:
            existing_signed_url = cache.get(str(obj.account_id) + 'profile_picture')
            if existing_signed_url:
                return existing_signed_url
            
            singed_url = accounts_utilities.generate_signed_url(obj.profile_picture.name)
            cache.set(str(obj.account_id) + 'profile_picture', singed_url, timeout=3600) 

            return singed_url

        return '/default-user-icon.svg'


class StudentAccountDetailsSerializer(serializers.ModelSerializer):

    identifier = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ['name', 'surname', 'email_address', 'identifier', 'role', 'image', 'account_id']
    
    def get_identifier(self, obj):
        """Return the identifier for the user: ID number, passport number, or email."""
        return obj.id_number or obj.passport_number

    def get_image(self, obj):
        if obj.profile_picture:
            existing_signed_url = cache.get(str(obj.account_id) + 'profile_picture')
            if existing_signed_url:
                return existing_signed_url
            
            singed_url = accounts_utilities.generate_signed_url(obj.profile_picture.name)
            cache.set(str(obj.account_id) + 'profile_picture', singed_url, timeout=3600) 

            return singed_url

        return '/default-user-icon.svg'


class StudentBasicAccountDetailsEmailSerializer(serializers.ModelSerializer):

    image = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ['name', 'surname', 'identifier', 'image']
            
    def get_identifier(self, obj):
        """Return the identifier for the user: ID number, passport number, or email."""
        return obj.id_number or obj.passport_number

    def get_image(self, obj):
        if obj.profile_picture:
            existing_signed_url = cache.get(str(obj.account_id) + 'profile_picture')
            if existing_signed_url:
                return existing_signed_url
            
            singed_url = accounts_utilities.generate_signed_url(obj.profile_picture.name)
            cache.set(str(obj.account_id) + 'profile_picture', singed_url, timeout=3600) 

            return singed_url

        return '/default-user-icon.svg'


class LeastAccountDetailsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Student
        fields = ['name', 'surname']
