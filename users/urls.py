# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # my info
    path('my-id/<int:invalidator>/', views.my_id, name='returns user info'),
    path('my-profile/<int:invalidator>/', views.my_profile, name='returns user info'),
    path('my-details/<int:invalidator>/', views.my_profile, name='returns user info'),
    path('my-profile-picture/<int:invalidator>/', views.my_image, name='returns user profile image'),
    path('my-email/<int:invalidator>/', views.my_email, name='returns user email'),
    path('my-names/<int:invalidator>/', views.my_names, name='returns user name and surname'),
    
    # profile picture change 
    path("update-profile-picture/", views.update_profile_picture, name="update user profile picture"),
    
    # principal account creation
    path('create-principal/<str:school_id>', views.create_principal, name="create school account"),
    path('principal-profile/<str:user_id>/<int:invalidator>/', views.create_principal, name="create school account"),
]
