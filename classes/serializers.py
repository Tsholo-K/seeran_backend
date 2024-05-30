# python 
import os
import datetime

# django
from django.core.cache import cache

# rest framework
from rest_framework import serializers

# models
from .models import Classroom

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



####################################### admindashboard serializer ############################################


# user security information
class ClassesSerializer(serializers.ModelSerializer):
    
    teacher = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = [ 'teacher', 'students', 'group', 'room_number', 'class_id' ]

    def get_teacher(self, obj):
        return obj.teacher.name.title() + ' ' + obj.teacher.surname.title()
    
    def get_students(self, obj):
        return obj.students.count()
