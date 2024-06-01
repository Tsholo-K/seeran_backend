# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # admindashboard urls
    path('teacher-schedule-days/<str:account_id>/', views.teacher_schedule_days, name='returns a specific teachers schedule days'),

]
