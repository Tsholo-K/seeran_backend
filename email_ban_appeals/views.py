# models
from .models import EmailBan

# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response

# custom decorators
from authentication.decorators import token_required
from users.decorators import founder_only

# serializers
from .serializers import EmailBansSerializer



# Create your views here.
@api_view(['GET'])
@token_required
def email_bans(request):
    email_bans = EmailBan.objects.filter(email=request.user.email).order_by('-banned_at')
    serializer = EmailBansSerializer(email_bans, many=True)
    
    return Response({ "bans" : serializer.data },status=200)
