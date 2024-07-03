# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # principal account urls
    path('principal-invoices/<str:account_id>/', views.principal_invoices, name="create school account"),
    
]