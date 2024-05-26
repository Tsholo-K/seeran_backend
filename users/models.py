# django imports
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import IntegrityError

# python 
import uuid

# models
from schools.models import School

# utility functions
from authentication.utils import get_upload_path, is_phone_number_valid


class CustomUserManager(BaseUserManager):
    
    # user creation 
    def create_user(self, email=None, id_number=None, name=None, surname=None, phone_number=None, role=None, school=None, **extra_fields):
        if not email and not id_number:
            raise ValueError(_('either email or ID number must be set'))
        
        if email:
            email = self.normalize_email(email)
            
        if role != 'FOUNDER' and school is None:
            raise ValueError(_('user must be part of a school'))
        
        if role == 'PRINCIPAL':
            if phone_number is None:
                raise ValueError(_('user must have a contact number'))
            if not is_phone_number_valid(phone_number):
                raise ValueError(_('invalid phone number format'))

        user = self.model(email=email, id_number=id_number, name=name, surname=surname, phone_number=phone_number, role=role, school=school, **extra_fields)
        return user
        
    
    # user first sign-in activation
    def activate_user(self, email, password):

        # try finding the user using the provided email 
        try:
            user = self.get(email=email)
    
        except self.model.DoesNotExist:
            return "User not found"

        # Validate the password
        try:
            validate_password(password)
     
        except ValidationError as e:
            return str(e)

        # Hash and salt the password
        user.set_password(password)
        user.activated = True
      
        # save the updated user to the database
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
    
    # needed feilds 
    email = models.EmailField(_('email address'), unique=True, blank=True, null=True)
    id_number = models.CharField(_('ID number'), max_length=13, unique=True, blank=True, null=True)
    name = models.CharField(_('name'), max_length=32)
    surname = models.CharField(_('surname'), max_length=32)
    phone_number = models.CharField(_('phone number'), max_length=9, unique=True, blank=True, null=True)
    user_id = models.CharField(max_length=15, unique=True)

    school = models.ForeignKey(School, on_delete=models.SET_NULL, related_name='users', null=True)
    
    activated = models.BooleanField(_('account active or not'), default=False)
    
    # profile picutre
    profile_picture = models.ImageField(upload_to=get_upload_path, blank=True, null=True)
    
    # choices for the role field
    ROLE_CHOICES = [
        ('STUDENT', 'Student'),
        ('TEACHER', 'Teacher'),
        ('ADMIN', 'Admin'),
        ('PRINCIPAL', 'Principal'),
        ('FOUNDER', 'Founder'),
        # Add more roles as needed
    ]
    # Role field
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="STUDENT")
    
    # children field
    children = models.ManyToManyField('self', blank=True)
    
    # permissions needed by django do not change( unless you have a valid reason to )
    is_active = models.BooleanField(_('active'), default=True)
    is_staff = models.BooleanField(_('staff status'), default=False)
    is_superuser = models.BooleanField(_('superuser status'), default=False)
    
    # email communication preferance
    event_emails = models.BooleanField(_('email subscription'), default=False)

    # multi-factor authentication
    multifactor_authentication = models.BooleanField(_('multifactor authentication'), default=False)
    
    email_banned = models.BooleanField(_('email banned'), default=False)
    email_ban_amount = models.SmallIntegerField(_('amount of times email has been banned'), default=0)
    
    # field for authentication
    USERNAME_FIELD = 'email' 
    
    # all required fields
    REQUIRED_FIELDS = ['name', 'surname', 'school', 'role']

    objects = CustomUserManager()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return self.email if self.email else self.id_number

    # overwirte save method
    def save(self, *args, **kwargs):
        if not self.user_id:
            self.user_id = self.generate_unique_account_id('UA')

        attempts = 0
        while attempts < 5:
            try:
                super().save(*args, **kwargs)
                break
            except IntegrityError:
                # If an IntegrityError is raised, it means the user_id was not unique.
                # Generate a new user_id and try again.
                self.user_id = self.generate_unique_account_id('UA') # user account
                attempts += 1
        if attempts >= 5:
            raise ValueError('Could not create user with unique user ID after 5 attempts. Please try again later.')

    @staticmethod
    def generate_unique_account_id(prefix=''):
        while True:
            unique_part = uuid.uuid4().hex
            account_id = prefix + unique_part
            account_id = account_id[:15].ljust(15, '0')

            if not CustomUser.objects.filter(user_id=account_id).exists():
                return account_id
            