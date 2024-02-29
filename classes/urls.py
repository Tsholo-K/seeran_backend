from django.urls import path
from . import views

urlpatterns = [
    path('class/<str:class_id>', views.create_user )
]