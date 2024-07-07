# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # bug reports
    path('report-bug/', views.create_bug_report, name="create bug report"),
    path('my-bug-reports/', views.my_bug_reports, name="get all users bug reports"),

    path('unresolved-bug-reports/', views.unresolved_bug_reports, name="get all unresolved bug reports"),
    path('resolved-bug-reports/', views.resolved_bug_reports, name="get all resolved bug reports"),

    path('resolved-bug-report/<str:bug_report_id>/', views.resolved_bug_report, name="get a resolved bug report"),
    path('resolved-bug-report/<str:bug_report_id>/', views.unresolved_bug_report, name="get a unresolved bug report"),

    path('update-bug-report-status/<str:bug_report_id>/', views.update_bug_report_status, name="update bug report status"),
    
]