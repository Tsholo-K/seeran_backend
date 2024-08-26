# python 

# httpx

# channels

# django

# simple jwt

# models 
from users.models import Principal, Admin, Teacher, Student, Parent

# serializers
from users.serializers.general_serializers import DisplayAccountDetailsSerializer, SourceAccountSerializer
from users.serializers.principals.principals_serializers import PrincipalAccountDetailsSerializer
from users.serializers.admins.admins_serializers import AdminAccountCreationSerializer, AdminAccountUpdateSerializer, AdminAccountDetailsSerializer
from users.serializers.teachers.teachers_serializers import TeacherAccountCreationSerializer, TeacherAccountUpdateSerializer, TeacherAccountDetailsSerializer
from users.serializers.students.students_serializers import StudentAccountCreationSerializer, StudentAccountUpdateSerializer, StudentAccountDetailsSerializer
from users.serializers.parents.parents_serializers import ParentAccountCreationSerializer, ParentAccountUpdateSerializer, ParentAccountDetailsSerializer

# utility functions 

# checks


account_creation_model_and_serializer_mapping = {
    'PARENT': (Parent, ParentAccountCreationSerializer),
    'ADMIN': (Admin, AdminAccountCreationSerializer),
    'TEACHER': (Teacher, TeacherAccountCreationSerializer),
    'STUDENT': (Student, StudentAccountCreationSerializer),
}

account_update_serializer_mapping = {
    'PARENT': ParentAccountUpdateSerializer,
    'ADMIN': AdminAccountUpdateSerializer,
    'TEACHER': TeacherAccountUpdateSerializer,
    'STUDENT': StudentAccountUpdateSerializer,
}

account_access_control_mapping = {
    'PRINCIPAL': Principal,
    'ADMIN': Admin,
    'TEACHER': Teacher,
    'STUDENT': Student,
}

account_model_details_and_attr_serializer_mapping = {
    'PARENT': (Parent, ParentAccountDetailsSerializer, None, 'children__school'),
    'PRINCIPAL': (Principal, PrincipalAccountDetailsSerializer, 'school', None),
    'ADMIN': (Admin, AdminAccountDetailsSerializer, 'school', None),
    'TEACHER': (Teacher, TeacherAccountDetailsSerializer, 'school', None),
    'STUDENT': (Student, StudentAccountDetailsSerializer, 'school', None),
}

account_details_serializer_mapping = {
    'PARENT': ParentAccountDetailsSerializer,
    'PRINCIPAL': PrincipalAccountDetailsSerializer,
    'ADMIN': AdminAccountDetailsSerializer,
    'TEACHER': TeacherAccountDetailsSerializer,
    'STUDENT': StudentAccountDetailsSerializer,
}

account_model_and_attr_mapping = {
    'PARENT': (Parent, None, 'children__school, children__enrolled_classes'),
    'PRINCIPAL': (Principal, 'school', None),
    'ADMIN': (Admin, 'school', None),
    'TEACHER': (Teacher, 'school', 'taught_classes__students'),
    'STUDENT': (Student, 'school', 'enrolled_classes'),
}
