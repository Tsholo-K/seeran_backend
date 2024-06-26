# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # bug reports
    path('report-bug/', views.create_bug_report, name="create school account"),
    path('unresolved-bug-reports/', views.unresolved_bug_reports, name="get all active bug reports"),
    path('resolved-bug-reports/', views.resolved_bug_reports, name="get all resolved bug reports"),
    path('bug-report/<str:bug_report_id>/', views.bug_report, name="get  bug report"),
    path('update-bug-report-status/<str:bug_report_id>/', views.update_bug_report_status, name="update bug report status"),
    
]