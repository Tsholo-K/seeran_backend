# models
from .models import EmailBan

# django
from django.views.decorators.cache import cache_control
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

# custom decorators
from authentication.decorators import token_required

# serializers
from .serializers import EmailBansSerializer, EmailBanSerializer, AppealEmailBanSerializer


@api_view(['GET'])
@token_required
def email_bans(request):
    email_bans = EmailBan.objects.filter(email=request.user.email).order_by('-banned_at')
    serializer = EmailBansSerializer(email_bans, many=True)
    
    return Response({ "email_bans" : serializer.data, 'strikes' : request.user.email_ban_amount, 'banned' : request.user.email_banned }, status=status.HTTP_200_OK)

@api_view(['GET'])
@token_required
@cache_control(max_age=120, private=True)
def email_ban(request, email_ban_id, invalidator):
    try:
        email_ban = EmailBan.objects.get(ban_id=email_ban_id)
        serializer = EmailBanSerializer(email_ban)
        return Response({ "email_ban" : serializer.data }, status=status.HTTP_200_OK)
    except ObjectDoesNotExist:
        return Response({ "error" : "invalid email ban id" }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH'])
@token_required
def appeal(request, email_ban_id):
    try:
        email_ban_appeal = EmailBan.objects.get(ban_id=email_ban_id)
        if email_ban_appeal.appeal is not None:
            return Response({ "error" : "An appeal has already been made for this ban" }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = AppealEmailBanSerializer(email_ban_appeal, data=request.data, partial=True)
        
        if serializer.is_valid():
            email_ban_appeal.appealed_at = timezone.now()
            serializer.save()
            return Response({ "message" : 'appeal submitted successfully' }, status=status.HTTP_200_OK)
        else:
            return Response({'error' : serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    except ObjectDoesNotExist:
        return Response({ "error" : "invalid email ban id" }, status=status.HTTP_400_BAD_REQUEST)