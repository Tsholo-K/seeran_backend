# rest framework
from rest_framework import serializers

# models
from .models import AdminAccountPermission, TeacherAccountPermission


class AdminPermissionsSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdminAccountPermission
        fields = ['action', 'target_model']


class TeacherPermissionsSerializer(serializers.ModelSerializer):

    class Meta:
        model = TeacherAccountPermission
        fields = ['action', 'target_model']


