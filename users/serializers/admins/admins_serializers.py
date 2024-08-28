# python 

# django

# rest framework
from rest_framework import serializers

# models
from users.models import Admin


class AdminAccountCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Admin
        fields = ['name', 'surname', 'email', 'school', 'role']

    def __init__(self, *args, **kwargs):
        super(AdminAccountCreationSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.fields['email'].validators = []


class AdminAccountUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Admin
        fields = ['name', 'surname', 'email']

    def __init__(self, *args, **kwargs):
        super(AdminAccountUpdateSerializer, self).__init__(*args, **kwargs)
        self.fields['email'].validators = []
        # Make all fields optional 
        for field in self.fields:
            self.fields[field].required = False


class AdminSecurityInformationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Admin
        fields = ['multifactor_authentication']
    

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
        return obj.email
        
    def get_role(self, obj):
        return obj.role.title()
            
    def get_image(self, obj):
        return obj.profile_picture.url if obj.profile_picture else '/default-user-icon.svg'


