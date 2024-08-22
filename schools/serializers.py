# python 


# rest framework
from rest_framework import serializers

# django
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

# models
from .models import School, Term
from users.models import CustomUser
from balances.models import Balance

# serializers
from users.serializers import AccountSerializer


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
    students = serializers.IntegerField()
    parents = serializers.IntegerField()
    teachers = serializers.IntegerField()
    
    class Meta:
        model = School
        fields = [ "school_id", 'name', 'students', 'parents', 'teachers', ]
        
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
            principal = CustomUser.objects.get(school=obj, role='PRINCIPAL')
            if principal:
                return AccountSerializer(principal).data
        except CustomUser.DoesNotExist:
            return None
    
    def get_balance(self, obj):
        try:
            principal = CustomUser.objects.get(school=obj, role='PRINCIPAL')
            if principal:
                balance = Balance.objects.get(user=principal)
                return { "amount" : str(balance.amount), "last_updated" : balance.last_updated.isoformat() }
  
        except CustomUser.DoesNotExist:
            return None
    
    def get_name(self, obj):
        return obj.name.title()
    
    
class SchoolDetailsSerializer(serializers.ModelSerializer):
        
    name = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    district = serializers.SerializerMethodField()
    province = serializers.SerializerMethodField()
    
    students = serializers.IntegerField()
    parents = serializers.IntegerField()
    teachers = serializers.IntegerField()
    admins = serializers.IntegerField()
    
    class Meta:
        model = School
        fields = ['name', 'type', 'district',  'province', 'email', 'contact_number', 'school_id',  'students', 'parents', 'teachers', 'admins', ]
        
    def get_name(self, obj):
        return obj.name.title()
    
    def get_type(self, obj):
        return obj.type.title()

    def get_district(self, obj):
        return obj.district.title()

    def get_province(self, obj):
        return obj.province.title()

class SchoolIDSerializer(serializers.ModelSerializer):
        
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


class TermCreationSerializer(serializers.ModelSerializer):
        
    class Meta:
        model = Term
        fields = [ "term", 'weight', 'start_date', 'end_date', 'school_days', 'school' ]


class UpdateSchoolTermSerializer(serializers.ModelSerializer):

    class Meta:
        model = Term
        fields = [ 'weight', 'start_date', 'end_date', 'school_days' ]

    def __init__(self, *args, **kwargs):
        super(UpdateSchoolAccountSerializer, self).__init__(*args, **kwargs)
        # Set all fields to be optional by making them not required
        for field in self.fields:
            self.fields[field].required = False


class TermsSerializer(serializers.ModelSerializer):
        
    class Meta:
        model = Term
        fields = [ "term", 'weight', 'start_date', 'end_date', 'term_id' ]


class TermSerializer(serializers.ModelSerializer):
        
    class Meta:
        model = Term
        fields = [ "term", 'weight', 'start_date', 'end_date', 'school_days' ]