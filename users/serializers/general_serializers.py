# rest framework
from rest_framework import serializers

# models
from users.models import BaseUser


class BasicAccountDetailsSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = BaseUser
        fields = ['name', 'surname', 'image', 'account_id']
    
    def get_name(self, obj):
        """Return the formatted name of the user."""
        return obj.name.title()

    def get_surname(self, obj):
        """Return the formatted surname of the user."""
        return obj.surname.title()
            
    def get_image(self, obj):
        """Return the URL of the user's image or a default image."""
        return obj.profile_picture.url if obj.profile_picture else '/default-user-icon.svg'


class BasicAccountDetailsEmailSerializer(serializers.ModelSerializer):

    image = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()

    class Meta:
        model = BaseUser
        fields = ['name', 'surname', 'identifier', 'image']
            
    def get_identifier(self, obj):
        """Return the email of the user."""
        return obj.email_address
            
    def get_image(self, obj):
        """Return the URL of the user's image or a default image."""
        return obj.profile_picture.url if obj.profile_picture else '/default-user-icon.svg'
    

class SourceAccountSerializer(serializers.ModelSerializer):

    identifier = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = BaseUser
        fields = ['name', 'surname', 'identifier', 'account_id', 'image']
                
    def get_image(self, obj):
        """Return the URL of the user's image or a default image."""
        return obj.profile_picture.url if obj.profile_picture else '/default-user-icon.svg'

    def get_identifier(self, obj):
        """Return the identifier for the user: email."""
        return obj.email_address


class BareAccountDetailsSerializer(serializers.ModelSerializer):

    class Meta:
        model = BaseUser
        fields = ['name', 'surname', 'account_id']


class DisplayAccountDetailsSerializer(serializers.ModelSerializer):

    image = serializers.SerializerMethodField()

    class Meta:
        model = BaseUser
        fields = [ 'name', 'surname', 'image' ]
            
    def get_image(self, obj):
        return obj.profile_picture.url if obj.profile_picture else '/default-user-icon.svg'
