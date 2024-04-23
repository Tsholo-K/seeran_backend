# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # bug reports
    path('report-bug/', views.create_bug_report, name="create school account"),
    path('bug-reports/<int:invalidator>/', views.bug_reports, name="get all active bug reports"),
    
]