from django.urls import path
from . import views

urlpatterns = [
    
    # user info
    path('userinfo/', views.user_info, name='returns user info'),
    path('useremail/', views.user_email, name='returns user email'),
    path('usernames/', views.user_names, name='returns user name and surname'),
    path('accountstatus/', views.account_status, name='checks if account is activated'),
    
    # authentication
    path('authenticate/', views.authenticate, name='get name and surname'),
    
    # email change
    path('validateemail/', views.validate_email, name='validate users email before email change'),
    path('changeemail/', views.change_email, name='change users email'),
    
    # password change
    path('validatepassword/', views.validate_password, name='validate users password before password change'),
    path('changepassword/', views.change_password, name='change users password'),   
    path('setpassword/', views.set_password, name='set account password( account activation )'),
    
    # password reset
    path('otpverification/', views.otp_verification, name='validate user before password reset'),
    path('resetpassword/', views.reset_password, name='reset users password'),
    
    # verification
    path('verifyotp/', views.verify_otp, name='otp authentication'),
    
    # otp
    path('resendotp/', views.resend_otp, name='request new otp'),
    
    # login
    path('login/', views.login, name='token obtain pair'),
    
    # sign in
    path('signin/', views.signin, name='first time sign in'),
    
    # logout
    path('logout/', views.logout, name='user logout'),
    
]
