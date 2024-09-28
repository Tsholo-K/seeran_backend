# rest framework
from rest_framework import serializers

# models
from users.models import Student


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

    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ['name', 'surname', 'identifier', 'account_id', 'image']
    
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
        return obj.id_number or obj.passport_number


class StudentAccountDetailsSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ['name', 'surname', 'email_address', 'identifier', 'role', 'image', 'account_id']
    
    def get_name(self, obj):
        return obj.name.title()
    
    def get_surname(self, obj):
        return obj.surname.title()
    
    def get_identifier(self, obj):
        """Return the identifier for the user: ID number, passport number, or email."""
        return obj.id_number or obj.passport_number
      
    def get_role(self, obj):
        return obj.role.title()
            
    def get_image(self, obj):
        return obj.profile_picture.url if obj.profile_picture else '/default-user-icon.svg'


class StudentBasicAccountDetailsEmailSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ['name', 'surname', 'identifier', 'image']
    
    def get_name(self, obj):
        """Return the formatted name of the user."""
        return obj.name.title()

    def get_surname(self, obj):
        """Return the formatted surname of the user."""
        return obj.surname.title()
            
    def get_identifier(self, obj):
        """Return the identifier for the user: ID number, passport number, or email."""
        return obj.id_number or obj.passport_number
            
    def get_image(self, obj):
        """Return the URL of the user's image or a default image."""
        return obj.profile_picture.url if obj.profile_picture else '/default-user-icon.svg'

class LeastAccountDetailsSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ['name', 'surname']
    
    def get_name(self, obj):
        return obj.name.title()
    
    def get_surname(self, obj):
        return obj.surname.title()
