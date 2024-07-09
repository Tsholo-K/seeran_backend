# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # bug reports
    path('report-bug/', views.create_bug_report, name="create bug report"),
    path('my-bug-reports/', views.my_bug_reports, name="get all users bug reports"),
    path('my-bug-report/<str:bug_report_id>/', views.my_bug_report, name="get users bug report"),

    path('update-bug-report-status/<str:bug_report_id>/', views.update_bug_report_status, name="update bug report status"),
    
]