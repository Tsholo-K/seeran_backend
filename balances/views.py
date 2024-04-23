# django
from django.views.decorators.cache import cache_control

# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response

# custom decorators
from authentication.decorators import token_required
from users.decorators import founder_only

# models 
from .models import Bill
from users.models import CustomUser

# serializers
from .serializers import BillsSerializer


# get principal invoices
@api_view(['GET'])
@cache_control(max_age=300, private=True)
@token_required
@founder_only
def principal_invoices(request, user_id, invalidator):
    try:
        # Get the principal instance
        principal = CustomUser.objects.get(account_id=user_id)
    except CustomUser.DoesNotExist:
        return Response({"error" : "user not found"}, status=404)
    # Get the principal's bills
    principal_bills = Bill.objects.filter(user=principal)
    if not principal_bills:
        return Response({"invoices" : None}, status=200)
    # Serialize the bills
    serializer = BillsSerializer(principal_bills, many=True)
    return Response({ "invoices" : serializer.data }, status=200)

