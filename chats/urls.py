# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    # admindashboard urls
    path('', views.hi, name='hi'),

]
