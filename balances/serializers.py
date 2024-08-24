# rest framework
from rest_framework import serializers

# models
from .models import Balance, Bill

# serializers
from users.serializers.founder.founder_serializers import BySerializer


### users balance serilizers ###


# user profile information
class BalanceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Balance
        fields = [ 'amount', 'last_updated' ]


# user profile information
class BillsSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Bill
        fields = [ 'amount', 'date_billed', 'is_paid', 'bill_id' ]


class BillSerializer(serializers.ModelSerializer):

    user = serializers.SerializerMethodField()
 
    class Meta:
        model = Bill
        fields = ['user', 'amount', 'date_billed', 'is_paid']

    def get_user(self, obj):
        if obj.user:
            return BySerializer(obj.user).data
        else:
            return None
                