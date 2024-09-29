# rest framework
from rest_framework import serializers

# models
from .models import AdminPermission, TeacherPermission


class AdminPermissionsSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdminPermission
        fields = ['action', 'target_model']


class TeacherPermissionsSerializer(serializers.ModelSerializer):

    class Meta:
        model = TeacherPermission
        fields = ['action', 'target_model']


