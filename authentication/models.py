from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .utils import generate_account_id


class CustomUserManager(BaseUserManager):
    # user creation 
    def create_user(self, email=None, id_number=None, name=None, surname=None, **extra_fields):
        if not email and not id_number:
            raise ValueError(_('Either email or ID number must be set'))
        
        if email:
            email = self.normalize_email(email)
        
        user = self.model(email=email, id_number=id_number, name=name, surname=surname, **extra_fields)
        user.save(using=self._db)
        return user
    
    # user first sign-in activation
    def activate_user(self, user_id, password):
        try:
            user = self.get(id=user_id)
        except self.model.DoesNotExist:
            return "User not found"

        # Validate the password
        try:
            validate_password(password)
        except ValidationError as e:
            return str(e)

        # Hash and salt the password
        user.set_password(password)
        user.save(using=self._db)
        return user

    # super user 
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if not email:
            raise ValueError(_('The Email field must be set'))
        
        return self.create_user(email, password=password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_('email address'), unique=True, blank=True, null=True)
    id_number = models.CharField(_('ID number'), max_length=20, unique=True, blank=True, null=True)
    name = models.CharField(_('name'), max_length=150)
    surname = models.CharField(_('surname'), max_length=150)
    is_active = models.BooleanField(_('active'), default=True)
    is_staff = models.BooleanField(_('staff status'), default=False)
    is_superuser = models.BooleanField(_('superuser status'), default=False)
    
    # Role fields
    is_student = models.BooleanField(_('student status'), default=False)
    is_teacher = models.BooleanField(_('teacher status'), default=False)
    is_parent = models.BooleanField(_('parent status'), default=False)
    is_admin = models.BooleanField(_('admin status'), default=False)
    is_principal = models.BooleanField(_('principal status'), default=False)
    
    account_id = models.CharField(max_length=13, unique=True, default=generate_account_id)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'surname']

    objects = CustomUserManager()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return self.email if self.email else self.id_number
