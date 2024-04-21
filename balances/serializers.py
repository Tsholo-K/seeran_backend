# rest framework
from rest_framework import serializers

# models
from .models import Balance


### users balance serilizers ###


# user profile information
class BalanceSerializer(serializers.ModelSerializer):
    
    image = serializers.SerializerMethodField()

    class Meta:
        model = Balance
        fields = [ 'amount', 'last_updated' ]
        