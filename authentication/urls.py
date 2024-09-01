from django.urls import path
from . import views

urlpatterns = [
    # login
    path('login/', views.login, name='token obtain pair'),
    
    # multi-factor authentication
    path('mfa-login/', views.multi_factor_authentication_login, name='two step verification'),
    
    # sign in
    path('sign-in/', views.signin, name='first time sign in'),
    path('verify-otp/', views.verify_otp, name='verifies otp during sign-in'),
    path('activate-account/', views.activate_account, name='set account password, final sign-in step'),

    # authentication
    path('authenticate/', views.authenticate, name='verify incoming request'),
    
    # password reset
    path('validate-password-reset/', views.validate_password_reset, name='verifies users email before password reset'),
    path('otp-verification/', views.password_reset_otp_verification, name='verifies users otp during password reset'),
    path('reset-password/', views.reset_password, name='resets users password'),
]
