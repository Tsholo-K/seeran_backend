# rest framework
from rest_framework import serializers

# django
from django.core.cache import cache

# models
from accounts.models import BaseAccount

# utility functions 
from accounts import utils as accounts_utilities


class ProfilePictureSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseAccount
        fields = ['profile_picture']

    def validate_profile_picture(self, value):
        # File size validation (limit to 5 MB for example)
        max_file_size = 25 * 1024 * 1024  # 5 MB
        if value.size > max_file_size:
            raise serializers.ValidationError("Could not process your request, file size must be under 25 MB.")

        # File type validation (allow only JPEG and PNG)
        if not value.name.lower().endswith(('.png', '.jpg', '.jpeg')):
            raise serializers.ValidationError("Could not process your request, file type must be JPEG or PNG.")

        # Image dimension validation
        # try:
        #     image = Image.open(value)
        #     max_width, max_height = 1920, 1080  # Set your desired dimensions
        #     if image.width > max_width or image.height > max_height:
        #         raise serializers.ValidationError(f"Image dimensions must be within {max_width}x{max_height} pixels.")
        # except Exception as e:
        #     raise ValidationError("Invalid image format or unable to open the image.")

        return value


class BasicAccountDetailsSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = BaseAccount
        fields = ['name', 'surname', 'image', 'account_id']
    
    def get_name(self, obj):
        """Return the formatted name of the user."""
        return obj.name.title()

    def get_surname(self, obj):
        """Return the formatted surname of the user."""
        return obj.surname.title()

    def get_image(self, obj):
        if obj.profile_picture:
            existing_signed_url = cache.get(str(obj.account_id) + 'profile_picture')
            if existing_signed_url:
                return existing_signed_url
            
            singed_url = accounts_utilities.generate_signed_url(obj.profile_picture.name)
            cache.set(str(obj.account_id) + 'profile_picture', singed_url, timeout=3600) 

            return singed_url

        return '/default-user-icon.svg'


class BasicAccountDetailsEmailSerializer(serializers.ModelSerializer):

    image = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()

    class Meta:
        model = BaseAccount
        fields = ['name', 'surname', 'identifier', 'image']
            
    def get_identifier(self, obj):
        """Return the email of the user."""
        return obj.email_address

    def get_image(self, obj):
        if obj.profile_picture:
            existing_signed_url = cache.get(str(obj.account_id) + 'profile_picture')
            if existing_signed_url:
                return existing_signed_url
            
            singed_url = accounts_utilities.generate_signed_url(obj.profile_picture.name)
            cache.set(str(obj.account_id) + 'profile_picture', singed_url, timeout=3600) 

            return singed_url

        return '/default-user-icon.svg'
    

class SourceAccountSerializer(serializers.ModelSerializer):

    identifier = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = BaseAccount
        fields = ['name', 'surname', 'identifier', 'account_id', 'image']

    def get_identifier(self, obj):
        """Return the identifier for the user: email."""
        return obj.email_address

    def get_image(self, obj):
        if obj.profile_picture:
            existing_signed_url = cache.get(str(obj.account_id) + 'profile_picture')
            if existing_signed_url:
                return existing_signed_url
            
            singed_url = accounts_utilities.generate_signed_url(obj.profile_picture.name)
            cache.set(str(obj.account_id) + 'profile_picture', singed_url, timeout=3600) 

            return singed_url

        return '/default-user-icon.svg'


class BareAccountDetailsSerializer(serializers.ModelSerializer):

    class Meta:
        model = BaseAccount
        fields = ['name', 'surname', 'account_id']


class DisplayAccountDetailsSerializer(serializers.ModelSerializer):

    image = serializers.SerializerMethodField()

    class Meta:
        model = BaseAccount
        fields = [ 'name', 'surname', 'image' ]

    def get_image(self, obj):
        if obj.profile_picture:
            existing_signed_url = cache.get(str(obj.account_id) + 'profile_picture')
            if existing_signed_url:
                return existing_signed_url
            
            singed_url = accounts_utilities.generate_signed_url(obj.profile_picture.name)
            cache.set(str(obj.account_id) + 'profile_picture', singed_url, timeout=3600) 

            return singed_url

        return '/default-user-icon.svg'
