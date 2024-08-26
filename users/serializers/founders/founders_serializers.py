# python 

# django

# rest framework
from rest_framework import serializers

# models
from users.models import Founder


class FounderAccountDetailsSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()

    class Meta:
        model = Founder
        fields = ['name', 'surname', 'role', 'image', 'identifier', 'account_id']
    
    def get_name(self, obj):
        return obj.name.title()
    
    def get_surname(self, obj):
        return obj.surname.title()
        
    def get_role(self, obj):
        return obj.role.title()
            
    def get_image(self, obj):
        return obj.profile_picture.url if obj.profile_picture else '/default-user-icon.svg'
    
    def get_identifier(self, obj):
        return obj.email


class FounderSecurityInformationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Founder
        fields = ['multifactor_authentication']

