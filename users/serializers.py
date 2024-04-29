# python 
import os
import datetime

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
    with open(os.path.join(BASE_DIR, 'private_key.pem'), 'rb') as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())
key_id = 'K1E45RUK43W3WT'
cloudfront_signer = CloudFrontSigner(key_id, rsa_signer)



### users serilizers ###


# user profile information
class MyProfileSerializer(serializers.ModelSerializer):
    
    image = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [ 'name', 'surname', 'email', 'image', 'account_id', 'role' ]
        
    def get_image(self, obj):
        if not obj.profile_picture:
            s3_url = 'https://seeran-storage.s3.amazonaws.com/defaults/default-user-icon.svg'
        else:
            s3_url = obj.profile_picture.url
        cloudfront_url = s3_url.replace('https://seeran-storage.s3.amazonaws.com', 'https://d376l49ehaoi1m.cloudfront.net')
        # Calculate expiration time (current time + 1 hour)
        expiration_time = datetime.datetime.now() + datetime.timedelta(hours=1)
        signed_url = cloudfront_signer.generate_presigned_url(
            cloudfront_url, 
            date_less_than=expiration_time
        )
        return signed_url
    
    def get_role(self, obj):
        return obj.role.lower().title()       
        
# user security information
class MySecurityInfoSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CustomUser
        fields = [ 'multifactor_authentication', 'event_emails' ]



#### principal serilizers ###


# principal creation
class PrincipalCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = [ 'name', 'surname', 'email', 'school', 'role' ]

# principal profile
class PrincipalProfileSerializer(serializers.ModelSerializer):

    image = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [ 'name', 'surname', 'email', 'image', 'account_id', 'role' ]
    
    def get_role(self, obj):
        return obj.role.lower().title() 
    
    def get_image(self, obj):
        if not obj.profile_picture:
            s3_url = 'https://seeran-storage.s3.amazonaws.com/defaults/default-user-icon.svg'
        else:
            s3_url = obj.profile_picture.url
        cloudfront_url = s3_url.replace('https://seeran-storage.s3.amazonaws.com', 'https://d376l49ehaoi1m.cloudfront.net')
        # Calculate expiration time (current time + 1 hour)
        expiration_time = datetime.datetime.now() + datetime.timedelta(minutes=5)
        signed_url = cloudfront_signer.generate_presigned_url(
            cloudfront_url, 
            date_less_than=expiration_time
        )
        return signed_url
        
