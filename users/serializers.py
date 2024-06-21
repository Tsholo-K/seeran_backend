# python 
import os
import datetime
from decouple import config

# django
from django.core.cache import cache

# rest framework
from rest_framework import serializers

# models
from .models import CustomUser

# cryptography
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

# boto
from botocore.signers import CloudFrontSigner

# root url 
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# cloudfront url signer 
def rsa_signer(message):
    with open(os.path.join(BASE_DIR, 'private_keys/cloudfront_private_key.pem'), 'rb') as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())
key_id = config('CLOUDFRONT_KEY_ID') # public key id
cloudfront_signer = CloudFrontSigner(key_id, rsa_signer)



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
      
        # if the user has no profile image return the default profile image 
        if not obj.profile_picture:
            s3_url =  config('AWS_STORAGE_BUCKET_DOMAIN') + '/defaults/default-user-icon.svg'
    
        # if they do have a profile image
        else:
            # try to get the users signed image url from cache
            s3_url = cache.get(str(obj.account_id) + 'profile_picture')
            
            # if its not there get their profile picture url from the db
            if s3_url == None:
                s3_url = obj.profile_picture.url
      
            # if there's a signed url in the cache return it instead
            else:
                return s3_url
       
        # make sure the url format is valid 
        cloudfront_url = s3_url.replace( config('AWS_STORAGE_BUCKET_DOMAIN'), config('CLOUDFRONT_CUSTOM_DOMAIN'))
        
        # Calculate expiration time (current time + 1 hour)
        expiration_time = datetime.datetime.now() + datetime.timedelta(hours=1)
       
        # sign the url
        signed_url = cloudfront_signer.generate_presigned_url(
            cloudfront_url, 
            date_less_than=expiration_time
        )
   
        # save it to cache for an hour
        cache.set(str(obj.account_id) + 'profile_picture', signed_url, timeout=3600)
        
        # return it 
        return signed_url
    

# user profile
class ProfilePictureSerializer(serializers.ModelSerializer):

    image = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [ 'image' ]
            
    def get_image(self, obj):
      
        # if the user has no profile image return the default profile image 
        if not obj.profile_picture:
            s3_url =  config('AWS_STORAGE_BUCKET_DOMAIN') + '/defaults/default-user-icon.svg'
    
        # if they do have a profile image
        else:
            # try to get the users signed image url from cache
            s3_url = cache.get(str(obj.account_id) + 'profile_picture')
            
            # if its not there get their profile picture url from the db
            if s3_url == None:
                s3_url = obj.profile_picture.url
      
            # if there's a signed url in the cache return it instead
            else:
                return s3_url
       
        # make sure the url format is valid 
        cloudfront_url = s3_url.replace( config('AWS_STORAGE_BUCKET_DOMAIN'), config('CLOUDFRONT_CUSTOM_DOMAIN'))
        
        # Calculate expiration time (current time + 1 hour)
        expiration_time = datetime.datetime.now() + datetime.timedelta(hours=1)
       
        # sign the url
        signed_url = cloudfront_signer.generate_presigned_url(
            cloudfront_url, 
            date_less_than=expiration_time
        )
   
        # save it to cache for an hour
        cache.set(str(obj.account_id) + 'profile_picture', signed_url, timeout=3600)
        
        # return it 
        return signed_url


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
      
        # if the user has no profile image return the default profile image 
        if not obj.profile_picture:
            s3_url =  config('AWS_STORAGE_BUCKET_DOMAIN') + '/defaults/default-user-icon.svg'
    
        # if they do have a profile image
        else:
            # try to get the users signed image url from cache
            s3_url = cache.get(str(obj.account_id) + 'profile_picture')
            
            # if its not there get their profile picture url from the db
            if s3_url == None:
                s3_url = obj.profile_picture.url
      
            # if there's a signed url in the cache return it instead
            else:
                return s3_url
       
        # make sure the url format is valid 
        cloudfront_url = s3_url.replace( config('AWS_STORAGE_BUCKET_DOMAIN'), config('CLOUDFRONT_CUSTOM_DOMAIN'))
        
        # Calculate expiration time (current time + 1 hour)
        expiration_time = datetime.datetime.now() + datetime.timedelta(hours=1)
       
        # sign the url
        signed_url = cloudfront_signer.generate_presigned_url(
            cloudfront_url, 
            date_less_than=expiration_time
        )
   
        # save it to cache for an hour
        cache.set(str(obj.account_id) + 'profile_picture', signed_url, timeout=3600)
        
        # return image url 
        return signed_url

