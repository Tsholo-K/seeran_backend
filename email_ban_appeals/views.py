# models
from .models import EmailBan

# django
from django.views.decorators.cache import cache_control
from django.core.exceptions import ObjectDoesNotExist

# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

# custom decorators
from authentication.decorators import token_required
from users.decorators import founder_only

# serializers
from .serializers import EmailBansSerializer, EmailBanSerializer, EmailBanAppealsSerializer, EmailBanAppealSerializer, AppealEmailBanSerializer


@api_view(['GET'])
@token_required
def email_bans(request):
    email_bans = EmailBan.objects.filter(email=request.user.email).order_by('-banned_at')
    serializer = EmailBansSerializer(email_bans, many=True)
    
    return Response({ "email_bans" : serializer.data },status=200)

@api_view(['GET'])
@token_required
def email_ban(request, email_ban_id):
    try:
        email_ban = EmailBan.objects.get(ban_id=email_ban_id)
        serializer = EmailBanSerializer(email_ban)
        return Response({ "email_ban" : serializer.data }, status=200)
    except ObjectDoesNotExist:
        return Response({ "error" : "invalid email ban id" }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@token_required
@founder_only
def email_ban_appeals(request):
    email_ban_appeals = EmailBan.objects.filter(status='PENDING', appeal__isnull=False).order_by('-appealed_at')
    serializer = EmailBanAppealsSerializer(email_ban_appeals, many=True)
    
    return Response({ "appeals" : serializer.data },status=200)

@api_view(['GET'])
@token_required
@founder_only
def email_ban_appeal(request, email_ban_appeal_id):
    try:
        email_ban_appeal = EmailBan.objects.get(ban_id=email_ban_appeal_id)
        serializer = EmailBanAppealSerializer(email_ban_appeal, many=True)
        
        return Response({ "appeal" : serializer.data },status=200)
    except ObjectDoesNotExist:
        return Response({ "error" : "invalid email ban id" }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PATCH'])
@token_required
def appeal(request, email_ban_appeal_id):
    try:
        email_ban_appeal = EmailBan.objects.get(ban_id=email_ban_appeal_id)
        serializer = AppealEmailBanSerializer(email_ban_appeal, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({ "message" : 'appeal submitted successfully' }, status=status.HTTP_200_OK)
        else:
            return Response({'error' : serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    except ObjectDoesNotExist:
        return Response({ "error" : "invalid email ban id" }, status=status.HTTP_400_BAD_REQUEST)