# models
from .models import EmailBan

# django
from django.views.decorators.cache import cache_control
from django.core.exceptions import ObjectDoesNotExist

# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response

# custom decorators
from authentication.decorators import token_required
from users.decorators import founder_only

# serializers
from .serializers import EmailBansSerializer, EmailBanSerializer, EmailBanAppealsSerializer, EmailBanAppealSerializer


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
        return Response({ "error" : "Invalid ban_id" }, status=400)

@api_view(['GET'])
@token_required
@founder_only
def email_ban_appeal(request, email_ban_appeal_id):
    email_ban_appeal = EmailBan.objects.get(ban_id=email_ban_appeal_id)
    serializer = EmailBanAppealSerializer(email_ban_appeal, many=True)
    
    return Response({ "appeal" : serializer.data },status=200)

@api_view(['GET'])
@token_required
@founder_only
def unresolved_email_ban_appeals(request):
    email_ban_appeals = EmailBan.objects.filter(status='PENDING', appeal__isnull=False).order_by('-appealed_at')
    serializer = EmailBanAppealsSerializer(email_ban_appeals, many=True)
    
    return Response({ "appeals" : serializer.data },status=200)

# get resolved bug reports
@api_view(["GET"])
@cache_control(max_age=3600, private=True)
@token_required
@founder_only
def resolved_email_ban_appeals(request, invalidator):
    email_ban_appeals = EmailBan.objects.exclude(status="PENDING").order_by('-appealed_at')
    serializer = EmailBanAppealsSerializer(email_ban_appeals, many=True)
    
    return Response({ "appeals" : serializer.data },status=200)
