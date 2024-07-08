from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    # path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls') ),
    path('api/usrs/', include('users.urls') ),
    path('api/blnc/', include('balances.urls') ),
    path('api/bgrp/', include('bug_reports.urls') ),
    path('api/ebap/', include('email_bans.urls') ),
    path('api/clss/', include('classes.urls') ),
    path('api/tmtb/', include('timetables.urls') ),
]
