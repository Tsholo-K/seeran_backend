# python 

# django

# rest framework
from rest_framework import serializers

# models
from users.models import Parent


class ParentAccountCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Parent
        fields = ['name', 'surname', 'email', 'role']

    def __init__(self, *args, **kwargs):
        super(ParentAccountCreationSerializer, self).__init__(*args, **kwargs)
        # remove email validation
        self.fields['email'].validators = []


class ParentAccountUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Parent
        fields = ['name', 'surname', 'email']

    def __init__(self, *args, **kwargs):
        super(ParentAccountUpdateSerializer, self).__init__(*args, **kwargs)
        # Make all fields optional 
        for field in self.fields:
            self.fields[field].required = False
        self.fields['email'].validators = []


class ParentSecurityInformationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Parent
        fields = ['multifactor_authentication', 'event_emails']
    

class ParentAccountDetailsSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = Parent
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
