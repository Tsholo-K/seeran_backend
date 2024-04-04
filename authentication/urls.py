from django.urls import path
from . import views

urlpatterns = [
    path('userinfo/', views.user_info, name='get name and surname'),
    path('authenticate/', views.authenticate, name='get name and surname'),
    path('login/', views.login, name='token obtain pair'),
    path('signin/', views.signin, name='first time sign in'),
    path('verifyotp/', views.verify_otp, name='otp authentication'),
    path('setpassword/', views.set_password, name='set account password'),
    path('accountstatus/', views.account_status, name='check if account is activated'),
    path('resendotp/', views.resend_otp, name='request new otp'),
    path('logout/', views.logout, name='user logout'),
]
