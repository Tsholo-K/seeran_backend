# python 
from decouple import config

# django
from django.core.cache import cache

# rest framework
from rest_framework import serializers

# models
from .models import CustomUser



########################################## general ##############################################


# user security information
class SecurityInfoSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CustomUser
        fields = [ 'multifactor_authentication', 'event_emails' ]


# user profile
class ProfileSerializer(serializers.ModelSerializer):

    role = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    surname = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [ 'name', 'surname', 'email', 'id', 'role', 'image' ]
    
    def get_name(self, obj):
        return obj.name.title()
    
    def get_surname(self, obj):
        return obj.surname.title()
    
    def get_id(self, obj):
        return obj.account_id
    
    def get_role(self, obj):
        return obj.role.title()
            
    def get_image(self, obj):
      
        return '/default-user-image.svg'
    

# user profile
class ProfilePictureSerializer(serializers.ModelSerializer):

    image = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [ 'image' ]
            
    def get_image(self, obj):
      
        return '/default-user-image.svg'


###################################################################################################



################################### founderdashboard serilizers ###################################


# principal creation 
class PrincipalCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = [ 'name', 'surname', 'phone_number', 'email', 'school', 'role' ]


###################################################################################################



################################### admindashboard serilizers #####################################


# user account creation
class UserCreationSerializer(serializers.ModelSerializer):

    email = serializers.EmailField(required=False)  # Make email optional
    id_number = serializers.CharField(required=False)  # Make id number optional
    grade = serializers.IntegerField(required=False)  # Make id number optional

    class Meta:
        model = CustomUser
        fields = [ 'name', 'surname', 'id_number', 'email', 'school', 'role', 'grade' ]


# users serializers 
class UsersSerializer(serializers.ModelSerializer):

    image = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [ 'name', 'surname', 'id', 'image' ]
    
    def get_id(self, obj):
        return obj.account_id
            
    def get_image(self, obj):
      
        return '/default-user-image.svg'

