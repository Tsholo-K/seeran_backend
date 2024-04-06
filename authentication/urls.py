from django.urls import path
from . import views

urlpatterns = [
    path('userinfo/', views.user_info, name='get users info'),
    path('useremail/', views.user_email, name='get users email'),
    path('usernames/', views.user_names, name='get users email'),
    path('authenticate/', views.authenticate, name='get name and surname'),
    path('login/', views.login, name='token obtain pair'),
    path('validateemail/', views.validate_email, name='validate users email before email change'),
    path('changeemail/', views.change_email, name='change users email'),
    path('validatepassword/', views.validate_password, name='validate users password before email change'),
    path('changepassword/', views.change_password, name='change users password'),
    path('resetpassword/', views.reset_password, name='reset users password'),
    path('signin/', views.signin, name='first time sign in'),
    path('verifyotp/', views.verify_otp, name='otp authentication'),
    path('setpassword/', views.set_password, name='set account password'),
    path('accountstatus/', views.account_status, name='check if account is activated'),
    path('resendotp/', views.resend_otp, name='request new otp'),
    path('logout/', views.logout, name='user logout'),
]
