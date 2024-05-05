from django.urls import path
from . import views

urlpatterns = [
    
    # email ban urls,
    path('email-bans/', views.email_bans, name="return users email bans"),
    path('email-ban/<str:email_ban_id>/<int:invalidator>/', views.email_ban, name="return a specific email ban"),
    
    path('send-otp/<str:email_ban_id>/', views.send_otp, name="user email ban appeal end point"),
    path('revalidate-email/<str:email_ban_id>/', views.revalidate_email, name="verify otp and revalidate users email"),
    
]
