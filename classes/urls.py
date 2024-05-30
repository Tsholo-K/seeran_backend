# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # admindashboard urls
    path('teacher-classes/<str:user_id>/', views.teacher_classes, name='returns a specific teachers classes'),
    path('register-classes/<str:grade>/', views.register_classes, name='returns all register classes in a grade'),

]
