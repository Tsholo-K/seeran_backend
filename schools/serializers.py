# python 
import os
import datetime

# rest framework
from rest_framework import serializers

# models
from .models import School
from authentication.models import CustomUser

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
    with open(os.path.join(BASE_DIR, 'private_key.pem'), 'rb') as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())
key_id = 'K1E45RUK43W3WT'
cloudfront_signer = CloudFrontSigner(key_id, rsa_signer)



class SchoolSerializer(serializers.ModelSerializer):
        
    name = serializers.SerializerMethodField()
    learners = serializers.IntegerField()
    parents = serializers.IntegerField()
    number_of_classes = serializers.SerializerMethodField()
    principal = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = ['name', 'email', 'contact_number', 'school_type', 'province', 'school_district', 'balance', 'learners', 'parents', 'number_of_classes', 'principal', ]

    def get_name(self, obj):
        return obj.name.title()
    
    def get_number_of_classes(self, obj):
        return ['']
    
    def get_principal(self, obj):
        try:
            principal = CustomUser.objects.get(school=obj, role='PRINCIPAL')
        except CustomUser.DoesNotExist:
            return None
        if principal:
            if not principal.profile_picture:
                s3_url = 'https://seeran-storage.s3.amazonaws.com/defaults/default-user-icon.svg'
            else:
                s3_url = principal.profile_picture.url
            cloudfront_url = s3_url.replace('https://seeran-storage.s3.amazonaws.com', 'https://d376l49ehaoi1m.cloudfront.net')
            # Calculate expiration time (current time + 1 hour)
            expiration_time = datetime.datetime.now() + datetime.timedelta(hours=1)
            signed_url = cloudfront_signer.generate_presigned_url(
                cloudfront_url, 
                date_less_than=expiration_time
            )
            return {
                'user_image': signed_url,
                # add any other fields you want to include
            }
        else:
            return None
    
    

class SchoolsSerializer(serializers.ModelSerializer):
    
    name = serializers.SerializerMethodField()
    learners = serializers.IntegerField()
    parents = serializers.IntegerField()
    number_of_classes = serializers.SerializerMethodField()
    
    class Meta:
        model = School
        fields = [ "school_id", 'name', 'learners', 'parents', 'number_of_classes', ]
        
    def get_name(self, obj):
        return obj.name.title()
    
    def get_number_of_classes(self, obj):
        return ['']