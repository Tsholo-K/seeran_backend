# python 
import os
import datetime

# rest framework
from rest_framework import serializers

# django
from django.core.cache import cache
from django.db.models import Q

# models
from .models import School
from users.models import CustomUser
from balances.models import Balance

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


class SchoolCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = School
        fields = [ 'name', 'email', 'contact_number', 'school_type', 'province', 'school_district' ]


class SchoolsSerializer(serializers.ModelSerializer):
    
    name = serializers.SerializerMethodField()
    students = serializers.IntegerField()
    parents = serializers.IntegerField()
    teachers = serializers.IntegerField()
    
    class Meta:
        model = School
        fields = [ "school_id", 'name', 'students', 'parents', 'teachers', ]
        
    def get_name(self, obj):
        return obj.name.title()
    

class SchoolSerializer(serializers.ModelSerializer):
        
    name = serializers.SerializerMethodField()
    principal = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()
    parents = serializers.SerializerMethodField()
    teachers = serializers.SerializerMethodField()
    admins = serializers.SerializerMethodField()
    school_type = serializers.SerializerMethodField()
    school_district = serializers.SerializerMethodField()
    province = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = ['name', 'school_type', 'school_district',  'province', 'email', 'contact_number', 'school_id', 'principal', 'balance',  'students', 'parents', 'teachers', 'admins', ]
        
    def get_name(self, obj):
        return obj.name.title()
    
    def get_school_type(self, obj):
        return obj.school_type.title()

    def get_school_district(self, obj):
        return obj.school_district.title()

    def get_province(self, obj):
        return obj.province.title()

    def get_students(self, obj):
        return CustomUser.objects.filter(role='STUDENT', school=obj).count()

    def get_parents(self, obj):
        return CustomUser.objects.filter(role='PARENT', school=obj).count()

    def get_teachers(self, obj):
        return CustomUser.objects.filter(role='TEACHER', school=obj).count()

    def get_admins(self, obj):
        return CustomUser.objects.filter(Q(role='ADMIN') | Q(role='PRINCIPAL'), school=obj).count()
        
    def get_principal(self, obj):
    
        try:
            principal = CustomUser.objects.get(school=obj, role='PRINCIPAL')
     
        except CustomUser.DoesNotExist:
            return None
      
        if principal:
            
            # if the user has no profile image return the default profile image 
            if not principal.profile_picture:
                s3_url = 'https://seeranbucket.s3.amazonaws.com/defaults/default-user-icon.svg'
        
            # if they do have a profile image
            else:
                # try to get the users signed image url from cache
                s3_url = cache.get(principal.email + 'profile_picture')
                
                # if its not there get their profile picture url from the db
                if s3_url == None:
                    s3_url = principal.profile_picture.url
        
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
            cache.set(principal.email + 'profile_picture', signed_url, timeout=3600)
        
            return {
                "name" : principal.name,
                "surname" : principal.surname,
                "id" : principal.user_id,
                'image': signed_url,
                # add any other fields you want to include
            }
        
        else:
            return None
    
    def get_balance(self, obj):

        try:
            principal = CustomUser.objects.get(school=obj, role='PRINCIPAL')
  
        except CustomUser.DoesNotExist:
            return None
 
        if principal:
            balance = Balance.objects.get(user=principal)
            return {
                "amount" : balance.amount,
                "last_updated" : balance.last_updated,
                # add any other fields you want to include
            }
    
        else:
            return None
    
    
