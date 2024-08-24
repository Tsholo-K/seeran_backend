from django.contrib import admin

# models
from users.models import BaseUser

# Register your models here.
admin.site.register(BaseUser)