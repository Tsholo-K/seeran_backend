# rest framework
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

# models
from .models import AdminPermissionGroup, TeacherPermissionGroup


class AdminPermissionGroupCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdminPermissionGroup
        fields = ['group_name', 'description', 'school']

    def __init__(self, *args, **kwargs):
        super(AdminPermissionGroupCreationSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]
        self.fields['description'].required = False


class TeacherPermissionGroupCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = TeacherPermissionGroup
        fields = ['assessor', 'title', 'assessment_type', 'total', 'percentage_towards_term_mark', 'start_time', 'dead_line', 'term', 'classroom', 'subject', 'grade', 'school', 'moderator']

    def __init__(self, *args, **kwargs):
        super(TeacherPermissionGroupCreationSerializer, self).__init__(*args, **kwargs)
        # Remove the unique together validator that's added by DRF
        self.validators = [v for v in self.validators if not isinstance(v, UniqueTogetherValidator)]
        self.fields['description'].required = False

