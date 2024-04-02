from django.urls import path
from . import views

urlpatterns = [
    path('credentials/', views.get_credentials, name='get name and surname'),
    path('login/', views.login, name='token obtain pair'),
    path('signin/', views.signin, name='account activation'),
    path('logout/', views.user_logout, name='user logout'),
]
