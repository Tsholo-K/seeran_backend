# python 
import datetime
import os

# rest framework
from rest_framework import serializers

# cryptography
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

# boto
from botocore.signers import CloudFrontSigner

# models
from .models import EmailBan
from users.models import CustomUser

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



### email ban serilizers ###


# users email bans serializer   
class EmailBansSerializer(serializers.ModelSerializer):
    
    status = serializers.SerializerMethodField()
    strikes = serializers.SerializerMethodField()
    
    class Meta:
        model = EmailBan
        fields = [ 'can_appeal', 'reason', 'ban_id', 'banned_at', 'status', 'strikes' ]
        
    def get_status(self, obj):
        return obj.status.title()
    
    def get_strikes(self, obj):
        try:
            user = CustomUser.objects.get(email=obj.email)
        except CustomUser.DoesNotExist:
            return None
        if user:
            return user.email_ban_amount
        else:
            return None


# users email ban
class EmailBanSerializer(serializers.ModelSerializer):
    
    status = serializers.SerializerMethodField()

    class Meta:
        model = EmailBan
        fields = [ 'can_appeal', 'email', 'banned_at', 'reason', 'ban_id', 'status', 'appeal', 'appealed_at' ]
        
    def get_status(self, obj):
        return obj.status.title()
 
        
class EmailBanAppealsSerializer(serializers.ModelSerializer):

    status = serializers.SerializerMethodField()

    class Meta:
        model = EmailBan
        fields = [ 'appeal', 'status', 'ban_id', 'appealed_at' ]
        
    def get_status(self, obj):
        return obj.status.title()
        
        
class EmailBanAppealSerializer(serializers.ModelSerializer):
    
    user = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = EmailBan
        fields = [ 'email', 'appeal', 'status', 'ban_id', 'appealed_at', 'user', 'reason' ]

    def get_status(self, obj):
        return obj.status.title()

    def get_user(self, obj):
        try:
            user = CustomUser.objects.get(email=obj.email)
        except CustomUser.DoesNotExist:
            return None
        if user:
            if not user.profile_picture:
                s3_url = 'https://seeran-storage.s3.amazonaws.com/defaults/default-user-icon.svg'
            else:
                s3_url = user.profile_picture.url
            cloudfront_url = s3_url.replace('https://seeran-storage.s3.amazonaws.com', 'https://d376l49ehaoi1m.cloudfront.net')
            # Calculate expiration time (current time + 1 hour)
            expiration_time = datetime.datetime.now() + datetime.timedelta(minutes=5)
            signed_url = cloudfront_signer.generate_presigned_url(
                cloudfront_url, 
                date_less_than=expiration_time
            )
            return {
                "name" : user.name,
                "surname" : user.surname,
                "id" : user.role.title(),
                'image': signed_url,
                # add any other fields you want to include
            }
        else:
            return None
        

# users email ban
class AppealEmailBanSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmailBan
        fields = [ 'appeal' ]
        