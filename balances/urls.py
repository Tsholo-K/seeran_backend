# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # general urls
    path('bill/<str:bill_id>/', views.bill , name='get bill'),

    # founderdashboard urls
    path('principal-invoices/<str:account_id>/', views.principal_invoices, name="create school account"),
    
]