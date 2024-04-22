from django.urls import path
from . import views

urlpatterns = [
    
    # school account views
    path('create-school/', views.create_school, name="create school account"),
    path('schools/<int:invalidator>/', views.schools, name="get all school accounts"),
    path('school/<str:school_id>/<int:invalidator>/', views.school, name="get school info"),
    path('school-info/<str:school_id>/<int:invalidator>/', views.school_info, name="get school info"),
]
