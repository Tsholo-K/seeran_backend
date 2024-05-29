# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # my info
    path('my-security-info/', views.my_security_info, name='user security info'),

    # profile picture update 
    path("update-profile-picture/", views.update_profile_picture, name="update profile picture"),

    # general urls
    path('profile/', views.user_profile, name="get users profile information"),

    # principal account urls // for founderdashboard, 'FOUNDER' role required
    path('create-principal/<str:school_id>', views.create_principal, name="create principal account"),
    path('delete-principal/', views.delete_principal, name="delete principal account"),
        
    # admin account urls // for admindashboard, 'ADMIN' role required 
    path('create-user', views.create_user, name="create user account"),
    path('delete-user/', views.delete_user, name="delete user account"),
    path('users/', views.users, name="get school user accounts"),

]
