# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # general urls
    path('schedule/<str:schedule_id>/', views.schedule, name='returns a specific schedule sessions'),

    # admindashboard urls
    path('create-schedule/', views.create_schedule, name='create a schedule for a specific teacher'),
    path('delete-schedule/', views.delete_schedule, name='delete a specific schedule'),
    path('teacher-schedules/<str:account_id>/', views.teacher_schedules, name='returns a specific teachers schedules'),

]
