# rest framework
from rest_framework import serializers

# models
from .models import Invoice

# serializers
from users.serializers.general_serializers import SourceAccountSerializer


class InvoicesSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Invoice
        fields = [ 'amount', 'date_billed', 'is_paid', 'bill_id' ]


class InvoiceSerializer(serializers.ModelSerializer):

    user = serializers.SerializerMethodField()
 
    class Meta:
        model = Invoice
        fields = ['user', 'amount', 'date_billed', 'is_paid']

    def get_user(self, obj):
        if obj.user:
            return SourceAccountSerializer(obj.user).data
        else:
            return None
                