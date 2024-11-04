from django.urls import path
from . import views

urlpatterns = [
    # recieving api endpoint
    path('parse-email/', views.parse_email, name='recieves an email parses it, allocates a case if without and saves to db.'),
    
]
