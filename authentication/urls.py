from django.urls import path
from . import views

urlpatterns = [
    # login
    path('login/', views.login, name='token obtain pair'),
    
    # multi-factor authentication
    path('multi-factor-authentication-login/', views.multi_factor_authentication_login, name='two step verification'),
    
    # sign in
    path('account-activation-credentials-verification/', views.account_activation_credentials_verification, name='first time sign in'),
    path('account-activation-otp-verification/', views.account_activation_otp_verification, name='verifies otp during sign-in'),
    path('activate-account/', views.activate_account, name='set account password, final sign-in step'),

    # authentication
    path('authenticate/', views.authenticate, name='verify incoming request'),
    
    # password reset
    path('credentials-reset-email-verification/', views.credentials_reset_email_verification, name='verifies users email before credentials reset'),
    path('credentials-reset-otp-verification/', views.credentials_reset_otp_verification, name='verifies users otp during credentials reset'),
    path('reset-credentials/', views.reset_credentials, name='resets users credentials'),

    # logout
    path('logout/', views.log_out, name='logout endpoint'),
]
