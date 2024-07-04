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
    
    class Meta:
        model = Bill
        fields = [ 'amount', 'date_billed', 'is_paid', 'bill_id' ]


class BillSerializer(serializers.ModelSerializer):

    user = serializers.SerializerMethodField()
 
    class Meta:
        model = Bill
        fields = ['user', 'amount', 'date_billed', 'is_paid', 'bill_id']

    def get_user(self, obj):
        user = obj.user

        if user is not None:
            return {
                'name': user.name,
                'surname': user.surname,
                'email': user.email,
                'picture': user.profile_picture.url if user.profile_picture else None,
            }
        
        else:
            return None
                