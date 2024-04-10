from django.urls import path
from . import views

urlpatterns = [
    
    # school account creation
    path('sns/notifications', views.sns_endpoint, name="sns notifications endpoint"),
    
]
