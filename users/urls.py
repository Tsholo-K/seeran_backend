# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # school account creation
    path('create-principal/', views.create_principal, name="create school account"),

]
