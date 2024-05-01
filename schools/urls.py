from django.urls import path
from . import views

urlpatterns = [
    
    # school account views
    path('create-school/', views.create_school, name="create school account"),
    path('schools/', views.schools, name="get all school accounts"),
    path('school/<str:school_id>/<int:invalidator>/', views.school, name="get school info"),
]
