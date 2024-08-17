# django
from django.db.models.signals import m2m_changed, post_delete
from django.dispatch import receiver

# models
from .models import Classroom
from users.models import CustomUser



