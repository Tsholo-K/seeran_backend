from django.urls import path, include


urlpatterns = [
    # path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls') ),
    path('api/usrs/', include('users.urls') ),
    path('api/bgrp/', include('bug_reports.urls') ),
]
