# python 

# django
from django.utils.translation import gettext_lazy as _

# rest framework
from rest_framework import serializers

# models
from .models import AuditLog

# serializers


class GradeCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = AuditLog
        fields = ['major_subjects', 'none_major_subjects', 'grade', 'school']

