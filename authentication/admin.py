from django.contrib import admin

# models
from users.models import CustomUser

# Register your models here.
admin.site.register(CustomUser)