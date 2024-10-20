# rest framework
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

# models
from .models import AdminPermissionGroup, TeacherPermissionGroup

# serilializers
from account_permissions.serializers import AdminPermissionsSerializer, TeacherPermissionsSerializer


class AdminPermissionGroupCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdminPermissionGroup
        fields = ['group_name', 'description', 'school']

    def __init__(self, *args, **kwargs):
        super(AdminPermissionGroupCreationSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]
        self.fields['description'].required = False


class AdminPermissionGroupUpdatenSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdminPermissionGroup
        fields = ['group_name', 'description']

    def __init__(self, *args, **kwargs):
        super(AdminPermissionGroupCreationSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]
        for field in self.fields:
            field.required = False


class TeacherPermissionGroupCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = TeacherPermissionGroup
        fields = ['group_name', 'description', 'school']

    def __init__(self, *args, **kwargs):
        super(TeacherPermissionGroupCreationSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]
        self.fields['description'].required = False


class TeacherPermissionGroupUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = TeacherPermissionGroup
        fields = ['group_name', 'description']

    def __init__(self, *args, **kwargs):
        super(TeacherPermissionGroupCreationSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]
        for field in self.fields:
            field.required = False


class AdminPermissionGroupsSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdminPermissionGroup
        fields = ['group_name', 'subscribers_count', 'permissions_count', 'last_updated', 'permission_group_id']


class TeacherPermissionGroupsSerializer(serializers.ModelSerializer):

    class Meta:
        model = TeacherPermissionGroup
        fields = ['group_name', 'subscribers_count', 'permissions_count', 'last_updated', 'permission_group_id']


class AdminPermissionGroupSerializer(serializers.ModelSerializer):

    permissions = serializers.SerializerMethodField()

    class Meta:
        model = AdminPermissionGroup
        fields = ['group_name', 'permissions_count', 'description', 'timestamp', 'permissions']

    def get_permissions(self, obj):
        return AdminPermissionsSerializer(obj.permissions.all(), many=True).data


class TeacherPermissionGroupSerializer(serializers.ModelSerializer):

    permissions = serializers.SerializerMethodField()

    class Meta:
        model = TeacherPermissionGroup
        fields = ['group_name', 'permissions_count', 'description', 'timestamp', 'permissions']

    def get_permissions(self, obj):
        return TeacherPermissionsSerializer(obj.permissions.all(), many=True).data
