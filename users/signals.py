# django
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

# models
from .models import BaseUser


