# python 

# django

# rest framework
from rest_framework import serializers

# models
from .models import CustomUser


class PrincipalAccountCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = [ 'name', 'surname', 'phone_number', 'email', 'school', 'role' ]


class StudentAccountCreationSerializer(serializers.ModelSerializer):

    email = serializers.EmailField(required=False, allow_blank=True)  # Make optional
    id_number = serializers.CharField(required=False, allow_blank=True)  # Make optional
    passport_number = serializers.CharField(required=False, allow_blank=True)  # Make optional

    class Meta:
        model = CustomUser
        fields = [ 'name', 'surname', 'id_number', 'passport_number', 'email', 'school', 'role', 'grade' ]


class ParentAccountCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = [ 'name', 'surname', 'email',  'role' ]


class AccountCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = [ 'name', 'surname', 'email', 'school', 'role', ]


class MySecurityInformationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CustomUser
        fields = [ 'multifactor_authentication', 'event_emails' ]


class MyAccountDetailsSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [ 'name', 'surname', 'identifier', 'image', 'role', 'id' ]
    
    def get_name(self, obj):
        return obj.name.title()
    
    def get_surname(self, obj):
        return obj.surname.title()
        
    def get_role(self, obj):
        return obj.role.title()
    
    def get_id(self, obj):
        return obj.account_id
            
    def get_image(self, obj):
        return '/default-user-image.svg'
    
    def get_identifier(self, obj):
        if obj.id_number:
            return obj.id_number
        if obj.passport_number:
            return obj.passport_number
        return obj.email


class AccountSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['name', 'surname', 'id', 'identifier', 'image']
    
    def get_id(self, obj):
        """Return the account ID of the user."""
        return obj.account_id
    
    def get_name(self, obj):
        """Return the formatted name of the user."""
        return obj.name.title()

    def get_surname(self, obj):
        """Return the formatted surname of the user."""
        return obj.surname.title()
            
    def get_image(self, obj):
        """Return the URL of the user's image or a default image."""
        # return obj.profile_picture.url if obj.image else '/default-user-image.svg'
        return '/default-user-image.svg'

    def get_identifier(self, obj):
        """Return the identifier for the user: ID number, passport number, or email."""
        return obj.id_number or obj.passport_number or obj.email



class AccountProfileSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [ 'name', 'surname', 'id', 'identifier', 'image' ]
    
    def get_name(self, obj):
        return obj.name.title()
    
    def get_surname(self, obj):
        return obj.surname.title()
                
    def get_id(self, obj):
        return obj.account_id

    def get_image(self, obj):
        return '/default-user-image.svg'

    def get_identifier(self, obj):
        if obj.id_number:
            return obj.id_number
        if obj.passport_number:
            return obj.passport_number
        return obj.email
    
    
class AccountIDSerializer(serializers.ModelSerializer):

    id = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [ 'email', 'name', 'surname', 'role', 'id', 'identifier' ]
    
    def get_name(self, obj):
        return obj.name.title()
    
    def get_surname(self, obj):
        return obj.surname.title()
    
    def get_role(self, obj):
        return obj.role.title()
    
    def get_id(self, obj):
        return obj.account_id
    
    def get_identifier(self, obj):
        if obj.id_number:
            return obj.id_number
        if obj.passport_number:
            return obj.passport_number
        return obj.email
    
    
class PrincipalIDSerializer(serializers.ModelSerializer):

    id = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [ 'email', 'name', 'surname', 'phone_number', 'role', 'id', 'identifier' ]
    
    def get_name(self, obj):
        return obj.name.title()
    
    def get_surname(self, obj):
        return obj.surname.title()
    
    def get_role(self, obj):
        return obj.role.title()
    
    def get_id(self, obj):
        return obj.account_id
    
    def get_identifier(self, obj):
        return obj.email
        

class PrincipalAccountUpdateSerializer(serializers.ModelSerializer):

    name = serializers.CharField(required=False)
    surname = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)  # Make email optional
    phone_number = serializers.CharField(required=False)

    class Meta:
        model = CustomUser
        fields = ['name', 'surname', 'email', 'phone_number']


class AccountUpdateSerializer(serializers.ModelSerializer):

    email = serializers.EmailField(required=False)  # Make email optional
    id_number = serializers.CharField(required=False)  # Make id number optional
    grade = serializers.IntegerField(required=False)  # Make grade number optional
    name = serializers.CharField(required=False)
    surname = serializers.CharField(required=False)

    class Meta:
        model = CustomUser
        fields = ['name', 'surname', 'id_number', 'email', 'grade']


class ChatroomSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [ 'name', 'surname', 'image' ]
    
    def get_name(self, obj):
        return obj.name.title()
    
    def get_surname(self, obj):
        return obj.surname.title()
            
    def get_image(self, obj):
        return '/default-user-image.svg'


class StudentAccountAttendanceRecordSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [ 'name', 'surname', 'identifier' ]
    
    def get_name(self, obj):
        return obj.name.title()
    
    def get_surname(self, obj):
        return obj.surname.title()
    
    def get_identifier(self, obj):
        if obj.id_number:
            return obj.id_number
        if obj.passport_number:
            return obj.passport_number
        return None


class StudentAccountClassCardSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [ 'name', 'surname', 'identifier', 'image' ]
    
    def get_name(self, obj):
        return obj.name.title()
    
    def get_surname(self, obj):
        return obj.surname.title()

    def get_image(self, obj):
        return '/default-user-image.svg'

    def get_identifier(self, obj):
        if obj.id_number:
            return obj.id_number
        if obj.passport_number:
            return obj.passport_number
        return obj.email