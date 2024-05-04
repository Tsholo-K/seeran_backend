# models
from .models import EmailBan, EmailBanAppeal

# django
from django.views.decorators.cache import cache_control

# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response

# custom decorators
from authentication.decorators import token_required
from users.decorators import founder_only

# serializers
from .serializers import EmailBansSerializer, EmailBanAppealsSerializer


@api_view(['GET'])
@token_required
def email_bans(request):
    email_bans = EmailBan.objects.filter(email=request.user.email).order_by('-banned_at')
    serializer = EmailBansSerializer(email_bans, many=True)
    
    return Response({ "email_bans" : serializer.data },status=200)

@api_view(['GET'])
@token_required
def email_ban(request, email_ban_id):
    email_bans = EmailBan.objects.get(ban_id=email_ban_id)
    serializer = EmailBansSerializer(email_bans)
    
    return Response({ "email_ban" : serializer.data },status=200)

@api_view(['GET'])
@token_required
@founder_only
def unresolved_email_ban_appeals(request):
    email_ban_appeals = EmailBanAppeal.objects.filter(status='PENDING').order_by('-appealed_at')
    serializer = EmailBanAppealsSerializer(email_ban_appeals, many=True)
    
    return Response({ "appeals" : serializer.data },status=200)

# get resolved bug reports
@api_view(["GET"])
@cache_control(max_age=3600, private=True)
@token_required
@founder_only
def resolved_email_ban_appeals(request, invalidator):
    email_ban_appeals = EmailBanAppeal.objects.exclude(status="PENDING").order_by('-appealed_at')
    serializer = EmailBanAppealsSerializer(email_ban_appeals, many=True)
    
    return Response({ "appeals" : serializer.data },status=200)