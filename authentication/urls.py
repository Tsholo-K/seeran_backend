from django.urls import path
from . import views

urlpatterns = [

    # authentication
    path('authenticate/', views.authenticate, name='get name and surname'),
    
    # email change
    path('change-email/', views.change_email, name='change users email'),
    
    # password change
    path('validate-password/', views.validate_password, name='verifies users password before password change'),
    path('change-password/', views.change_password, name='change users password'),   
    
    # password reset
    path('validate-password-reset/', views.validate_password_reset, name='verifies users email before password reset'),
    path('otp-verification/', views.otp_verification, name='verifies users otp before password reset'),
    path('reset-password/', views.reset_password, name='resets users password'),
    
    # otp generation
    path('resend-otp/', views.resend_otp, name='request new otp'),
    
    # login
    path('login/', views.login, name='token obtain pair'),
    
    # multi-factor authentication
    path('mfa-login/', views.multi_factor_authentication_login, name='change users multi-factor authentication prefferance'),
    
    # sign in
    path('sign-in/', views.signin, name='first time sign in'),
    path('activate-account/', views.activate_account, name='set account password( account activation )'),
    
]
