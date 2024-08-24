# python 


# rest framework
from rest_framework import serializers

# django

# models
from .models import School
from users.models import Principal
from balances.models import Balance

# serializers
from users.serializers.principals.principals_serializers import PrincipalAccountSerializer
from balances.serializers import BalanceSerializer


class SchoolCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = School
        fields = [ 'name', 'email', 'contact_number', 'type', 'province', 'district' ]


class UpdateSchoolAccountSerializer(serializers.ModelSerializer):

    class Meta:
        model = School
        fields = ['name', 'email', 'contact_number', 'type', 'district', 'operating_hours', 'location', 'website']

    def __init__(self, *args, **kwargs):
        super(UpdateSchoolAccountSerializer, self).__init__(*args, **kwargs)
        # Set all fields to be optional by making them not required
        for field in self.fields:
            self.fields[field].required = False


class SchoolsSerializer(serializers.ModelSerializer):
    
    name = serializers.SerializerMethodField()
    
    class Meta:
        model = School
        fields = ['name', 'student_count', 'teacher_count', 'admin_count', "school_id"]
        
    def get_name(self, obj):
        return obj.name.title()
    

class SchoolSerializer(serializers.ModelSerializer):
        
    principal = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = ['principal', 'balance', 'name' ]
                
    def get_principal(self, obj):
        try:
            principal = Principal.objects.get(school=obj, role='PRINCIPAL')
            return PrincipalAccountSerializer(principal).data
        except Principal.DoesNotExist:
            return None
    
    def get_balance(self, obj):
        try:
            principal = Principal.objects.get(school=obj, role='PRINCIPAL')
            balance = principal.balance
            return BalanceSerializer(balance).data
        except Principal.DoesNotExist:
            return None
    
    def get_name(self, obj):
        return obj.name.title()


class SchoolDetailsSerializer(serializers.ModelSerializer):
        
    name = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    district = serializers.SerializerMethodField()
    province = serializers.SerializerMethodField()
    
    class Meta:
        model = School
        fields = ['name', 'email', 'contact_number', 'in_arrears', 'type', 'province', 'district', 'operating_hours', 'location', 'website', 'school_id' ]
        
    def get_name(self, obj):
        return obj.name.title()
    
    def get_type(self, obj):
        return obj.type.title()

    def get_district(self, obj):
        return obj.district.title()

    def get_province(self, obj):
        return obj.province.title()

