from django.urls import path
from . import views

urlpatterns = [
    path('credentials/', views.get_credentials, name='get name and surname'),
    path('login/', views.login, name='token obtain pair'),
    path('signin/', views.signin, name='first time sign in'),
    path('otpverification/<str:email>', views.verify_otp_view, name='otp authentication'),
    path('accountactivated/', views.account_activated, name='check if account is activated'),
    path('logout/', views.user_logout, name='user logout'),
]
