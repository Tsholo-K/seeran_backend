from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.custom_token_obtain_pair, name='token_obtain_pair'),
    path('logout/', views.user_logout, name='user logout'),
]
