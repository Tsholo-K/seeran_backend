# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # principal account urls
    path('principal-invoices/<str:user_id>/<int:invalidator>/', views.principal_invoices, name="create school account"),
    
]