# rest framework
from rest_framework import serializers

# models
from .models import School
from accounts.models import Principal

# serializers
from accounts.serializers.principals.serializers import PrincipalAccountSerializer
from balances.serializers import BalanceSerializer


class SchoolCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = School
        fields = [ 'name', 'email_address', 'contact_number', 'type', 'province', 'district' ]

    def __init__(self, *args, **kwargs):
        super(SchoolCreationSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.fields['email_address'].validators = []
        self.fields['contact_number'].validators = []
    

class UpdateSchoolAccountSerializer(serializers.ModelSerializer):

    class Meta:
        model = School
        fields = [
            'name', 'email_address', 'contact_number', 'type', 'district', 'data_retention_period', 'operating_hours', 'location', 'website', 'logo', 'grading_system', 'library_details', 'laboratory_details', 'sports_facilities'
        ]

    def __init__(self, *args, **kwargs):
        super(UpdateSchoolAccountSerializer, self).__init__(*args, **kwargs)
        # Set all fields to be optional by making them not required
        for field in self.fields:
            self.fields[field].required = False


class SchoolsSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = School
        fields = ['name', 'student_count', 'teacher_count', 'admin_count', "school_id"]
    

class SchoolSerializer(serializers.ModelSerializer):
        
    principal = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = ['name', 'principal', 'balance']
                
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


class SchoolDetailsSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = School
        fields = ['name', 'email_address', 'contact_number', 'type', 'province', 'district', 'operating_hours', 'location', 'website', 'student_count', 'teacher_count', 'admin_count', 'in_arrears', 'school_id' ]

