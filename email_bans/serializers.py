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
    
    class Meta:
        model = EmailBan
        fields = [ 'can_appeal', 'reason', 'ban_id', 'banned_at', 'status' ]
        
    def get_status(self, obj):
        return obj.status.title()


# users email ban
class EmailBanSerializer(serializers.ModelSerializer):
    
    status = serializers.SerializerMethodField()

    class Meta:
        model = EmailBan
        fields = [ 'can_appeal', 'email', 'banned_at', 'reason', 'ban_id', 'status', 'otp_send' ]
        
    def get_status(self, obj):
        return obj.status.title()
 

# users email ban
class AppealEmailBanSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmailBan
        fields = [ 'appeal' ]
        