# python 
import os
import datetime

# rest framework
from rest_framework import serializers

# django
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
    with open(os.path.join(BASE_DIR, 'private_key.pem'), 'rb') as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())
key_id = 'K1E45RUK43W3WT'
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

    class Meta:
        model = School
        fields = ['name', 'school_type', 'school_district',  'province','email', 'contact_number', 'school_id', 'principal', 'balance',  'students', 'parents', 'teachers', 'admins', ]
        
    def get_name(self, obj):
        return obj.name.title()

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
                "name" : principal.name,
                "surname" : principal.surname,
                "id" : principal.account_id,
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

        
    name = serializers.SerializerMethodField()
    
    students = serializers.SerializerMethodField()
    parents = serializers.SerializerMethodField()
    teachers = serializers.SerializerMethodField()
    admins = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = ['name', 'email', 'contact_number', 'school_type', 'province', 'school_district', 'school_id', 'students', 'parents', 'teachers', 'admins', ]

    def get_name(self, obj):
        return obj.name.title()

    def get_students(self, obj):
        return CustomUser.objects.filter(role='STUDENT', school=obj).count()

    def get_parents(self, obj):
        return CustomUser.objects.filter(role='PARENT', school=obj).count()

    def get_teachers(self, obj):
        return CustomUser.objects.filter(role='TEACHER', school=obj).count()

    def get_admins(self, obj):
        return CustomUser.objects.filter(Q(role='ADMIN') | Q(role='PRINCIPAL'), school=obj).count()
    
