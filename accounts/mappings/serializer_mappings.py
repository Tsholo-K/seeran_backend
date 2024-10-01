# serializers
from accounts.serializers.general_serializers import SourceAccountSerializer
from accounts.serializers.founders.serializers import FounderSecurityInformationSerializer
from accounts.serializers.principals.serializers import PrincipalAccountDetailsSerializer, PrincipalSecurityInformationSerializer
from accounts.serializers.admins.serializers import AdminAccountCreationSerializer, AdminAccountUpdateSerializer, AdminAccountDetailsSerializer, AdminSecurityInformationSerializer
from accounts.serializers.teachers.serializers import TeacherAccountCreationSerializer, TeacherAccountUpdateSerializer, TeacherAccountDetailsSerializer, TeacherSecurityInformationSerializer
from accounts.serializers.students.serializers import StudentAccountCreationSerializer, StudentAccountUpdateSerializer, StudentAccountDetailsSerializer, StudentSecurityInformationSerializer, StudentSourceAccountSerializer
from accounts.serializers.parents.serializers import ParentAccountCreationSerializer, ParentAccountUpdateSerializer, ParentAccountDetailsSerializer, ParentSecurityInformationSerializer


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
