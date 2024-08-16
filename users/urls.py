# django 
from django.urls import path

# views
from . import views

urlpatterns = [
    
    # my info
    path('my-account-details/', views.my_account_details, name='users account info'),

    # profile picture update 
    # path("update-profile-picture/", views.update_profile_picture, name="update profile picture"),
    # path("remove_profile_picture/", views.remove_profile_picture, name="remove profile picture"),

]
