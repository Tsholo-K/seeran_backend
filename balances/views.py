# django
from django.views.decorators.cache import cache_control

# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

# custom decorators
from authentication.decorators import token_required
from users.decorators import founder_only

# models 
from .models import Bill
from users.models import CustomUser

# serializers
from .serializers import BillsSerializer, BillSerializer


############################################## founderdashboard view functions #######################################


@api_view(['GET'])
@token_required
def bill(request, bill_id):

    if request.user.role not in ["PRINCIPAL", "ADMIN", "PARENT", "FOUNDER"]:
        return Response({"error" : "invalid role for request, permission denied"}, status=status.HTTP_403_FORBIDDEN)

    try:
        # Get the bill instance
        bill = Bill.objects.get(bill_id=bill_id)
        
        if request.user.role == "FOUNDER" and bill.user.role != "PRINCIPAL" :
            return Response({"error" : "action forbidden, permission denied"}, status=status.HTTP_403_FORBIDDEN)
        
        if request.user.role in ["ADMIN", "PRINCIPAL"]:
            if request.user.school != bill.user.school or (bill.user.role == "PRINCIPAL" and request.user != bill.user):
                return Response({"error" : "request denied, invalid permissions"}, status=status.HTTP_403_FORBIDDEN)
        
        if request.user.role == "PARENT" and bill.user not in request.user.children:
            return Response({"error" : "invalid request, invalid permissions"}, status=status.HTTP_403_FORBIDDEN)
                
        # Serialize the bills
        serializer = BillSerializer(instance=bill)
        return Response({ "invoice" : serializer.data }, status=status.HTTP_200_OK)
    
    except Bill.DoesNotExist:
        return Response({"error" : "a bill with the provided ID can not be found"}, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        # if any exceptions rise during return the response return it as the response
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


######################################################################################################################



############################################## founderdashboard view functions #######################################


# get principal invoices
@api_view(['GET'])
@token_required
@founder_only
def principal_invoices(request, account_id):
    
    try:
        # Get the principal instance
        principal = CustomUser.objects.get(account_id=account_id)
        
        # Get the principal's bills
        principal_bills = Bill.objects.filter(user=principal).order_by('-date_billed')
        
        if not principal_bills:
            return Response({ 'message' : 'success', "invoices" : None, 'in_arrears': principal.school.in_arrears}, status=status.HTTP_200_OK)
        
        # Serialize the bills
        serializer = BillsSerializer(principal_bills, many=True)
        return Response({ 'message' : 'success', "invoices" : serializer.data, 'in_arrears': principal.school.in_arrears }, status=status.HTTP_200_OK)
    
    except CustomUser.DoesNotExist:
        return Response({"error" : "user with the provided credentials can not be found"}, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        # if any exceptions rise during return the response return it as the response
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


######################################################################################################################
