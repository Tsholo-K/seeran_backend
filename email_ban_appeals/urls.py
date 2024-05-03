from django.urls import path
from . import views

urlpatterns = [
    
    # email ban/appeals urls
    path('email-bans/', views.email_bans, name="return users email bans"),
    path('unresolved-email-ban-appeals/', views.unresolved_email_ban_appeals, name="return all unresolved email bana appeals"),
    path('unresolved-email-ban-appeals/<int:invalidator>/', views.unresolved_email_ban_appeals, name="return all unresolved email bana appeals"),
]
