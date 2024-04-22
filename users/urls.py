# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # my info
    path('my-id/<int:invalidator>/', views.my_id, name='returns user info'),
    path('my-profile/<int:invalidator>/', views.my_profile, name='returns user info'),
    path('my-details/<int:invalidator>/', views.my_details, name='returns user info'),
    path('my-security-info/<int:invalidator>/', views.my_security_info, name='returns user profile image'),
    
    # profile picture change 
    path("update-profile-picture/", views.update_profile_picture, name="update user profile picture"),
    
    # principal account urls
    path('create-principal/<str:school_id>', views.create_principal, name="create school account"),
    path('principal-profile/<str:user_id>/<int:invalidator>/', views.principal_profile, name="return principal profile information"),
    path('principal-id/<str:user_id>/<int:invalidator>/', views.principal_id, name="return principal profile information"),
    path('principal-info/<str:user_id>/<int:invalidator>/', views.principal_info, name="return principal profile information"),
    
]
