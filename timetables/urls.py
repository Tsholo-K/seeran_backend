# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # admindashboard urls
    path('teacher-schedules/<str:account_id>/', views.teacher_schedules, name='returns a specific teachers schedules'),
    path('create-schedule/', views.create_schedule, name='returns a specific teachers schedules'),

    path('schedule/<str:schedule_id>/', views.schedule, name='returns a specific schedule sessions'),

]
