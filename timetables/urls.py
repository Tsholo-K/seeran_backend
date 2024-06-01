# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # admindashboard urls
    path('teacher-schedules/<str:account_id>/', views.teacher_schedules, name='returns a specific teachers schedules'),

]
