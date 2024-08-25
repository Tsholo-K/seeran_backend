# python 

# django

# rest framework
from rest_framework import serializers

# models
from users.models import Student


class StudentAccountCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Student
        fields = ['name', 'surname', 'email', 'school', 'role']


class StudentAccountUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Student
        fields = ['name', 'surname', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields optional 
        for field in self.fields:
            self.fields[field].required = False


class StudentSecurityInformationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Student
        fields = ['multifactor_authentication', 'event_emails']
    

class StudentAccountSerializer(serializers.ModelSerializer):
    
    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ['name', 'surname', 'identifier', 'image', 'account_id']
    
    def get_name(self, obj):
        """Return the formatted name of the user."""
        return obj.name.title()

    def get_surname(self, obj):
        """Return the formatted surname of the user."""
        return obj.surname.title()
            
    def get_image(self, obj):
        """Return the URL of the user's image or a default image."""
        return obj.profile_picture.url if obj.profile_picture else '/default-user-icon.svg'

    def get_identifier(self, obj):
        """Return the identifier for the user: ID number, passport number, or email."""
        return obj.id_number or obj.passport_number or obj.email
    

class StudentAccountDetailsSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [ 'name', 'surname', 'identifier', 'role', 'image', 'account_id' ]
    
    def get_name(self, obj):
        return obj.name.title()
    
    def get_surname(self, obj):
        return obj.surname.title()
    
    def get_identifier(self, obj):
        return obj.id_number or obj.passport_number or obj.email
      
    def get_role(self, obj):
        return obj.role.title()
            
    def get_image(self, obj):
        return obj.profile_picture.url if obj.profile_picture else '/default-user-icon.svg'
    


class LeastAccountDetailsSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ['name', 'surname']
    
    def get_name(self, obj):
        return obj.name.title()
    
    def get_surname(self, obj):
        return obj.surname.title()
            
    def get_image(self, obj):
        return obj.profile_picture.url if obj.profile_picture else '/default-user-icon.svg'