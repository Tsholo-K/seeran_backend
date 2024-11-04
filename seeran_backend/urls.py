from django.urls import path, include


urlpatterns = [
    # path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls') ),
    path('api/upld/', include('uploads.urls') ),
    path('api/emails/', include('emails.urls') ),
]
