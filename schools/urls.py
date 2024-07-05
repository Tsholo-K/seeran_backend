from django.urls import path
from . import views

urlpatterns = [
    
    # founderdashboard urls
    path('create-school/', views.create_school, name="create school account"),
    path('schools/', views.schools, name="get all school accounts"),
    path('school/<str:school_id>/', views.school, name="get school info"),
    path('school-details/<str:school_id>/', views.school_details, name="get school info"),
    path('delete-school/', views.delete_school, name="create school account"),

]
