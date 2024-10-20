from django.urls import path, include


urlpatterns = [
    # path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls') ),
]
