from django.urls import path
from . import views

urlpatterns = [
    path('credentials/', views.get_credentials_view, name='get name and surname'),
    path('login/', views.login_view, name='token obtain pair'),
    path('signin/', views.signin_view, name='first time sign in'),
    path('verifyotp/', views.verify_otp_view, name='otp authentication'),
    path('setpassword/', views.set_password_view, name='set account password'),
    path('accountstatus/', views.account_status_view, name='check if account is activated'),
    path('resendotp/', views.resend_otp_view, name='request new otp'),
    path('logout/', views.user_logout_view, name='user logout'),
]
