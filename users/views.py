# python 
import random
import datetime
import os

# rest framework
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

# django
from django.views.decorators.cache import cache_control

# custom decorators
from authentication.decorators import token_required
from schools.decorators import founder_only

# models
from users.models import CustomUser
from schools.models import School
from balances.models import Balance

# serilializer
from .serializers import MyProfileSerializer, MyIDSerializer, MyDetailsSerializer, PrincipalCreationSerializer, PrincipalProfileSerializer

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




### users infomation views ###


# get users id info
@api_view(["GET"])
@cache_control(max_age=86400, private=True)
@token_required
def my_id(request, invalidator):
    serializer = MyIDSerializer(data=request.user)
    return Response({ "user" : serializer.data },status=200)


# get users profile info
@api_view(["GET"])
@cache_control(max_age=86400, private=True)
@token_required
def my_profile(request, invalidator):
    serializer = MyProfileSerializer(data=request.user)
    return Response({ "user" : serializer.data },status=200)


# get users profile info
@api_view(["GET"])
@cache_control(max_age=86400, private=True)
@token_required
def my_details(request, invalidator):
    serializer = MyDetailsSerializer(data=request.user)
    return Response({ "user" : serializer.data },status=200)


# get users image
@api_view(["GET"])
@cache_control(max_age=3600, private=True)
@token_required
def my_image(request, invalidator):
    if request.user.profile_picture == "":
        return Response({ "image_url" : None },status=200)
    s3_url = request.user.profile_picture.url
    cloudfront_url = s3_url.replace('https://seeran-storage.s3.amazonaws.com', 'https://d376l49ehaoi1m.cloudfront.net')
    # Calculate expiration time (current time + 1 hour)
    expiration_time = datetime.datetime.now() + datetime.timedelta(hours=1)
    signed_url = cloudfront_signer.generate_presigned_url(
        cloudfront_url, 
        date_less_than=expiration_time
    )
    return Response({ "image_url" : signed_url},status=200)


# get users email 
@api_view(["GET"])
@cache_control(max_age=86400, private=True)
@token_required
def my_email(request, invalidator):
    return Response({ "email" : request.user.email},status=200)


# get users name and surname
@api_view(["GET"])
@cache_control(max_age=86400, private=True)
@token_required
def my_names(request, invalidator):
    return Response({ "name" : request.user.name, "surname" : request.user.surname},status=200)





@api_view(['POST'])
@cache_control(max_age=120, private=True)
@token_required
@founder_only
def create_principal(request, school_id):
    try:
        # Get the school instance
        school = School.objects.get(school_id=school_id)
    except School.DoesNotExist:
        return Response({"error" : "School not found"})
    # Check if the school already has a principal
    if CustomUser.objects.filter(school=school, role="PRINCIPAL").exists():
        return Response({"error" : "This school already has a principal account linked to it"}, status=400)
    # Add the school instance to the request data
    data = request.data.copy()
    data['school'] = school.id
    data['role'] = "PRINCIPAL"

    serializer = PrincipalCreationSerializer(data=data)
    if serializer.is_valid():
        user = serializer.save()
        # Create a new Balance instance for the user
        Balance.objects.create(user=user)
        # Generate a random 6-digit number
        # this will invalidate the cache on the frontend
        random_number = random.randint(100000, 999999)
        return Response({ "message" : "principal account created successfully", "invalidator" : random_number }, status=201)
    return Response({"error" : serializer.errors}, status=400)


@api_view(['GET'])
@cache_control(max_age=120, private=True)
@token_required
@founder_only
def principal_profile(request, user_id, invalidator):
    try:
        # Get the school instance
        principal = CustomUser.objects.get(account_id=user_id)
    except CustomUser.DoesNotExist:
        return Response({"error" : "user not found"})
    # Add the school instance to the request data
    serializer = PrincipalProfileSerializer(data=principal)
    return Response({ "principal" : serializer.data }, status=201)



### user upload views ###


# user profile pictures upload 
@api_view(['PATCH'])
@parser_classes([MultiPartParser, FormParser])
@token_required
def update_profile_picture(request):
    profile_picture = request.FILES.get('profile_picture', None)
    if profile_picture:
        user = CustomUser.objects.get(email=request.user.email)  # get the current user
        user.profile_picture.delete()  # delete the old profile picture if it exists
        user.profile_picture.save(profile_picture.name, profile_picture)  # save the new profile picture
        user.save()
        # Generate a random 6-digit number
        # this will invalidate the cache on the frontend
        random_number = random.randint(100000, 999999)
        response = Response({"message": "picture updated successfully.", "invalidator" : random_number}, status=200)
        return response
    else:
        return Response({"error" : "No file was uploaded."}, status=400)



