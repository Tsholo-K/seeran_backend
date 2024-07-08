from django.urls import path
from . import views

urlpatterns = [
    
    # founderdashboard urls
    path('create-school/', views.create_school, name="create school account"),
    path('delete-school/', views.delete_school, name="create school account"),

]
