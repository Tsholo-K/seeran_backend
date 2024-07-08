# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # my info
    path('my-profile/', views.my_profile, name='user profile info'),

    # profile picture update 
    path("update-profile-picture/", views.update_profile_picture, name="update profile picture"),
    path("remove_profile_picture/", views.remove_profile_picture, name="remove profile picture"),

    # general urls
    path('profile/<str:account_id>/', views.user_profile, name="get users profile information"),

    # urls for founderdashboard, 'FOUNDER' role required
    path('delete-principal/', views.delete_principal, name="delete principal account"),
        
    # urls  for admindashboard, 'ADMIN' role required 
    path('delete-user/', views.delete_user, name="delete user account"),
    path('users/<str:role>/', views.users, name="get school admin or teacher accounts"),
    path('students/<str:grade>/', views.students, name="get student accounts in provided grade"),

]
