from django.urls import path
from . import views

urlpatterns = [
    
    # email ban urls,
    path('email-bans/', views.email_bans, name="return users email bans"),
    path('email-ban/<str:email_ban_id>/<int:invalidator>/', views.email_ban, name="return a specific email ban"),
    
    path('appeal/<str:email_ban_id>/', views.appeal, name="user email ban appeal end point"),
    
]
