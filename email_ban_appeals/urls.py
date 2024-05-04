from django.urls import path
from . import views

urlpatterns = [
    
    # email ban/appeals urls,
    path('email-bans/', views.email_bans, name="return users email bans"),
    path('email-ban/<str:email_ban_id>/', views.email_ban, name="return a specific email ban"),
    
    path('email-ban-appeals/', views.email_ban_appeals, name="return all unresolved email bana appeals"),
    path('email-ban-appeal/', views.email_ban_appeal, name="return a specific email ban appeal"),
    
    path('appeal/<str:email_ban_id>/', views.appeal, name="user email ban appeal end point"),
    
]
