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
        
    principal = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = ['principal', 'balance', 'name' ]
                
    def get_principal(self, obj):
    
        try:
            principal = CustomUser.objects.get(school=obj, role='PRINCIPAL')
     
        except CustomUser.DoesNotExist:
            return None
      
        if principal:
                    
            return {
                "name" : principal.name,
                "surname" : principal.surname,
                "id" : principal.account_id,
                'image': '/default-user-image.svg',
            }
        
        else:
            return None
    
    def get_balance(self, obj):

        try:
            principal = CustomUser.objects.get(school=obj, role='PRINCIPAL')
  
        except CustomUser.DoesNotExist:
            return None
 
        if principal:
            balance = Balance.objects.get(user=principal)
            return {
                "amount" : str(balance.amount),
                "last_updated" : balance.last_updated.isoformat(),
            }
    
        else:
            return None
    
    def get_name(self, obj):
        return obj.name.title()
    
    
class SchoolDetailsSerializer(serializers.ModelSerializer):
        
    name = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()
    parents = serializers.SerializerMethodField()
    teachers = serializers.SerializerMethodField()
    admins = serializers.SerializerMethodField()
    school_type = serializers.SerializerMethodField()
    school_district = serializers.SerializerMethodField()
    province = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = ['name', 'school_type', 'school_district',  'province', 'email', 'contact_number', 'school_id',  'students', 'parents', 'teachers', 'admins', ]
        
    def get_name(self, obj):
        return obj.name.title()
    
    def get_school_type(self, obj):
        return obj.school_type.title()

    def get_school_district(self, obj):
        return obj.school_district.title()

    def get_province(self, obj):
        return obj.province.title()

    def get_students(self, obj):
        return CustomUser.objects.filter(role='STUDENT', school=obj).count()

    def get_parents(self, obj):
        return CustomUser.objects.filter(role='PARENT', school=obj).count()

    def get_teachers(self, obj):
        return CustomUser.objects.filter(role='TEACHER', school=obj).count()

    def get_admins(self, obj):
        return CustomUser.objects.filter(Q(role='ADMIN') | Q(role='PRINCIPAL'), school=obj).count()
        
