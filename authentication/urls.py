from django.urls import path
from . import views

urlpatterns = [
    path('credentials/', views.get_credentials, name='get name and surname'),
    path('login/', views.login, name='token obtain pair'),
    path('signin/', views.signin, name='first time sign in'),
    path('verifyotp/', views.verify_otp_view, name='otp authentication'),
    path('setpassword/', views.set_password_view, name='set account password'),
    path('accountstatus/', views.account_activated, name='check if account is activated'),
    path('resendotp/', views.resend_otp, name='request new otp'),
    path('logout/', views.user_logout, name='user logout'),
]
