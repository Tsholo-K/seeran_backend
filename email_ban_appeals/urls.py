from django.urls import path
from . import views

urlpatterns = [
    
    # email ban appeals urls
    path('email-bans/', views.email_bans, name="return users email bans"),
]
