from django.urls import path

# views
from . import views


urlpatterns = [
    # login
    path('update-profile-picture/', views.update_profile_picture, name='profile picture update view'),

]