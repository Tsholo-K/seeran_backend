# serializers
from users.serializers.general_serializers import SourceAccountSerializer
from users.serializers.founders.founders_serializers import FounderSecurityInformationSerializer
from users.serializers.principals.principals_serializers import PrincipalAccountDetailsSerializer, PrincipalSecurityInformationSerializer
from users.serializers.admins.admins_serializers import AdminAccountCreationSerializer, AdminAccountUpdateSerializer, AdminAccountDetailsSerializer, AdminSecurityInformationSerializer
from users.serializers.teachers.teachers_serializers import TeacherAccountCreationSerializer, TeacherAccountUpdateSerializer, TeacherAccountDetailsSerializer, TeacherSecurityInformationSerializer
from users.serializers.students.students_serializers import StudentAccountCreationSerializer, StudentAccountUpdateSerializer, StudentAccountDetailsSerializer, StudentSecurityInformationSerializer, StudentSourceAccountSerializer
from users.serializers.parents.parents_serializers import ParentAccountCreationSerializer, ParentAccountUpdateSerializer, ParentAccountDetailsSerializer, ParentSecurityInformationSerializer


account_creation = {
    'PARENT': ParentAccountCreationSerializer,
    'ADMIN': AdminAccountCreationSerializer,
    'TEACHER': TeacherAccountCreationSerializer,
    'STUDENT': StudentAccountCreationSerializer,
}

account_update = {
    'PARENT': ParentAccountUpdateSerializer,
    'ADMIN': AdminAccountUpdateSerializer,
    'TEACHER': TeacherAccountUpdateSerializer,
    'STUDENT': StudentAccountUpdateSerializer,
}

account_profile = {
    'PARENT': SourceAccountSerializer,
    'PRINCIPAL': SourceAccountSerializer,
    'ADMIN': SourceAccountSerializer,
    'TEACHER': SourceAccountSerializer,
    'STUDENT': StudentSourceAccountSerializer,
}

account_details = {
    'PARENT': ParentAccountDetailsSerializer,
    'PRINCIPAL': PrincipalAccountDetailsSerializer,
    'ADMIN': AdminAccountDetailsSerializer,
    'TEACHER': TeacherAccountDetailsSerializer,
    'STUDENT': StudentAccountDetailsSerializer,
}

account_security_information = {
    'FOUNDER': FounderSecurityInformationSerializer,
    'PRINCIPAL': PrincipalSecurityInformationSerializer,    
    'PARENT': ParentSecurityInformationSerializer,
    'ADMIN': AdminSecurityInformationSerializer,
    'TEACHER':  TeacherSecurityInformationSerializer,
    'STUDENT': StudentSecurityInformationSerializer,
}
