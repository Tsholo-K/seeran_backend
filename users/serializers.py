# python 
import os
import datetime

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
key_id = 'K2HSBJR82PHOT4' # public keys id
cloudfront_signer = CloudFrontSigner(key_id, rsa_signer)



### users serilizers ###


# user profile information
class MyProfileSerializer(serializers.ModelSerializer):
    
    role = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [ 'name', 'surname', 'email', 'user_id', 'role', 'image' ]
            
    def get_role(self, obj):
        return obj.role.lower().title()
    
    def get_image(self, obj):
      
        # if the user has no profile image return the default profile image 
        if not obj.profile_picture:
            s3_url = 'https://seeranbucket.s3.amazonaws.com/defaults/default-user-icon.svg'
    
        # if they do have a profile image
        else:
            # try to get the users signed image url from cache
            s3_url = cache.get(obj.email + 'profile_picture')
            
            # if its not there get their profile picture url from the db
            if s3_url == None:
                s3_url = obj.profile_picture.url
      
            # if there's a signed url in the cache return it instead
            else:
                return s3_url
       
        # make sure the url format is valid 
        cloudfront_url = s3_url.replace('https://seeranbucket.s3.amazonaws.com', 'https://d31psdy2k7b4vc.cloudfront.net')
        
        # Calculate expiration time (current time + 1 hour)
        expiration_time = datetime.datetime.now() + datetime.timedelta(hours=1)
       
        # sign the url
        signed_url = cloudfront_signer.generate_presigned_url(
            cloudfront_url, 
            date_less_than=expiration_time
        )
   
        # save it to cache for an hour
        cache.set(obj.email + 'profile_picture', signed_url, timeout=3600)
        
        # return it 
        return signed_url



# user security information
class MySecurityInfoSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CustomUser
        fields = [ 'multifactor_authentication', 'event_emails' ]


# users image serializer
class GetImageSerializer(serializers.ModelSerializer):

    
    class Meta:
        model = CustomUser
        fields = [ 'image' ]



#### principal serilizers ###


# principal creation
class PrincipalCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = [ 'name', 'surname', 'email', 'school', 'role' ]


# principal profile
class PrincipalProfileSerializer(serializers.ModelSerializer):

    role = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [ 'name', 'surname', 'email', 'user_id', 'role', 'image' ]
    
    def get_role(self, obj):
        return obj.role.lower().title()
            
    def get_image(self, obj):
      
        # if the user has no profile image return the default profile image 
        if not obj.profile_picture:
            s3_url = 'https://seeranbucket.s3.amazonaws.com/defaults/default-user-icon.svg'
    
        # if they do have a profile image
        else:
            # try to get the users signed image url from cache
            s3_url = cache.get(obj.email + 'profile_picture')
            
            # if its not there get their profile picture url from the db
            if s3_url == None:
                s3_url = obj.profile_picture.url
      
            # if there's a signed url in the cache return it instead
            else:
                return s3_url
       
        # make sure the url format is valid 
        cloudfront_url = s3_url.replace('https://seeranbucket.s3.amazonaws.com', 'https://d31psdy2k7b4vc.cloudfront.net')
        
        # Calculate expiration time (current time + 1 hour)
        expiration_time = datetime.datetime.now() + datetime.timedelta(hours=1)
       
        # sign the url
        signed_url = cloudfront_signer.generate_presigned_url(
            cloudfront_url, 
            date_less_than=expiration_time
        )
   
        # save it to cache for an hour
        cache.set(obj.email + 'profile_picture', signed_url, timeout=3600)
        
        # return it 
        return signed_url
