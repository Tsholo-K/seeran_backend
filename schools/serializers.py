# python 


# rest framework
from rest_framework import serializers

# django
from django.db.models import Q

# models
from .models import School
from users.models import CustomUser
from balances.models import Balance



class SchoolCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = School
        fields = [ 'name', 'email', 'contact_number', 'school_type', 'province', 'school_district' ]


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
        
    name = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = ['principal', 'balance', 'name' ]
                
    def to_representation(self, instance):
        
        representation = super().to_representation(instance)
        principal = instance.principal
        if principal:
            representation['principal'] = {
                "name": principal.name,
                "surname": principal.surname,
                "id": principal.account_id,
                'image': '/default-user-image.svg',
            }
            balance = principal.balance
            if balance:
                representation['balance'] = {
                    "amount": str(balance.amount),
                    "last_updated": balance.last_updated.isoformat(),
                }
        return representation
    
    def get_name(self, obj):
        return obj.name.title()
    
    
class SchoolDetailsSerializer(serializers.ModelSerializer):
    
    students = serializers.IntegerField()
    parents = serializers.IntegerField()
    teachers = serializers.IntegerField()
    admins = serializers.IntegerField()

    class Meta:
        model = School
        fields = ['name', 'school_type', 'school_district', 'province', 'email', 'contact_number', 'school_id', 'students', 'parents', 'teachers', 'admins']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['name'] = instance.name.title()
        representation['school_type'] = instance.school_type.title()
        representation['school_district'] = instance.school_district.title()
        representation['province'] = instance.province.title()
        return representation
        
