from django.urls import path
from . import views

urlpatterns = [
    
    # school account creation
    path('create-school/', views.create_school, name="create school account"),
    path('schools/<int:invalidator>/', views.schools, name="get all school accounts"),
]
