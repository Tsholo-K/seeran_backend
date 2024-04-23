# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # principal account urls
    path('report-bug/', views.create_bug_report, name="create school account"),
    
]