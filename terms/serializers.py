# python 

# django
from django.utils.translation import gettext_lazy as _

# rest framework
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

# models
from .models import Term
from grades.models import Grade
from schools.models import School

# serializers
from classes.serializers import ClassesSerializer


class TermCreationSerializer(serializers.ModelSerializer):
    
    # explicitly declaring the field since its set as editable=False in the model, 
    # specifying that a field should not be included in forms autogenerated from the model. This includes the admin site and serializers in Django Rest Framework
    term = serializers.CharField(max_length=16) 
    grade = serializers.PrimaryKeyRelatedField(queryset=Grade.objects.all()) 
    school = serializers.PrimaryKeyRelatedField(queryset=School.objects.all())

    class Meta:
        model = Term
        fields = ['term', 'weight', 'start_date', 'end_date', 'school_days', 'grade', 'school']

    def __init__(self, *args, **kwargs):
        super(TermCreationSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]


class UpdateTermSerializer(serializers.ModelSerializer):

    class Meta:
        model = Term
        fields = [ 'weight', 'start_date', 'end_date', 'school_days' ]

    def __init__(self, *args, **kwargs):
        super(UpdateTermSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]
        # Set all fields to be optional by making them not required
        for field in self.fields:
            self.fields[field].required = False


class TermsSerializer(serializers.ModelSerializer):
            
    term = serializers.SerializerMethodField()

    class Meta:
        model = Term
        fields = ['term', 'weight', 'start_date', 'end_date', 'term_id']

    def get_term(self, obj):
        return obj.term.title()


class TermSerializer(serializers.ModelSerializer):
            
    term = serializers.SerializerMethodField()

    class Meta:
        model = Term
        fields = ['term', 'weight', 'start_date', 'end_date', 'school_days']
    
    def get_term(self, obj):
        return obj.term.title()

