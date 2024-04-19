from django.urls import path
from . import views

urlpatterns = [
    
    # aws sns endpoint
    path('sns/notifications', views.sns_endpoint, name="sns notifications endpoint"),
    
    # user info
    path('user-info/<int:invalidator>/', views.user_info, name='returns user info'),
    path('user-profile-picture/<int:invalidator>/', views.user_image, name='returns user profile image'),
    path('user-email/<int:invalidator>/', views.user_email, name='returns user email'),
    path('user-names/<int:invalidator>/', views.user_names, name='returns user name and surname'),
    path('account-status/', views.account_status, name='checks if account is activated'),
    
    # profile picture change 
    path("update-profile-picture/", views.update_profile_picture, name="update user profile picture"),
    
    # authentication
    path('authenticate/', views.authenticate, name='get name and surname'),
    
    # email change
    path('validate-email/', views.validate_email, name='validate users email before email change'),
    path('change-email/', views.change_email, name='change users email'),
    
    # password change
    path('validate-password/', views.validate_password, name='validate users password before password change'),
    path('change-password/', views.change_password, name='change users password'),   
    path('set-password/', views.set_password, name='set account password( account activation )'),
    
    # password reset
    path('otp-verification/', views.otp_verification, name='validate user before password reset'),
    path('reset-password/', views.reset_password, name='reset users password'),
    
    # multi-factor authentication
    path('mfa-login/', views.multi_factor_authentication, name='change users multi-factor authentication prefferance'),
    path('mfa-change/', views.mfa_change, name='change users multi-factor authentication prefferance'),
    path('mfa-status/', views.mfa_status, name='checks the multi-factor authentication status'),
    
    # verification
    path('verify-otp/', views.verify_otp, name='otp authentication'),
    
    # otp
    path('resend-otp/', views.resend_otp, name='request new otp'),
    
    # event emails subscription
    path('event-emails-subscription/', views.event_emails_subscription, name="event emails subscription"),
    
    # login
    path('login/', views.login, name='token obtain pair'),
    
    # sign in
    path('sign-in/', views.signin, name='first time sign in'),
    
    # logout
    path('log-out/', views.logout, name='user logout'),
    
]
