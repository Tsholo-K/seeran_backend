# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # my info
    path('my-profile/', views.my_profile, name='returns user info'),
    path('my-security-info/<int:invalidator>/', views.my_security_info, name='returns user profile image'),
    
    # profile picture change 
    path("update-profile-picture/", views.update_profile_picture, name="update user profile picture"),
    
    # principal account urls
    path('create-principal/<str:school_id>', views.create_principal, name="create school account"),
    path('delete-principal/', views.delete_principal, name="create school account"),
    path('principal-profile/<str:user_id>/<int:invalidator>/', views.principal_profile, name="return principal profile information"),
    path('principal-info/<str:user_id>/<int:invalidator>/', views.principal_info, name="return principal profile information"),
    
]
