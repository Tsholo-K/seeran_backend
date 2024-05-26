# rest framework
from rest_framework import serializers

# models
from .models import Balance, Bill


### users balance serilizers ###


# user profile information
class BalanceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Balance
        fields = [ 'amount', 'last_updated' ]


# user profile information
class BillsSerializer(serializers.ModelSerializer):
    
    in_arears = serializers.SerializerMethodField()

    class Meta:
        model = Bill
        fields = [ 'amount', 'date_billed', 'is_paid', 'bill_id', 'in_arears' ]
        
    def get_in_arears(self, obj):
        return obj.user.school.in_arears
        