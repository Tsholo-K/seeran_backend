# django imports
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

# python 
import uuid

# models
from schools.models import School
from grades.models import Grade

# utility functions
from authentication.utils import get_upload_path, is_phone_number_valid


class CustomUserManager(BaseUserManager):
    
    # user creation 
    def create_user(self, email=None, id_number=None, name=None, surname=None, phone_number=None, role=None, children=None, school=None, grade=None, **extra_fields):
          
        if not email and not id_number:
            raise ValueError(_('either email or ID number must be provided'))
     
        # Check if the email already exists in the system
        if email and self.model.objects.filter(email=email).exists():
            raise ValueError(_('An account with the provided email already exists'))

        # Check if the ID number already exists in the system
        if id_number and self.model.objects.filter(id_number=id_number).exists():
            raise ValueError(_('An account with the provided ID number already exists'))
        
        if role in ['STUDENT', 'TEACHER', 'ADMIN', 'PRINCIPAL']:
            if school is None:
                raise ValueError(_('Account must be associated with a school'))
        
        else:
            school = None # a parent/founder shouldnt be associated with a school
        
        if role == 'PRINCIPAL':
        
            if phone_number is None:      
                raise ValueError(_('Account must have a contact number'))
          
            if not is_phone_number_valid(phone_number):
                raise ValueError(_('invalid phone number format'))
        
        else:
            phone_number = None

        if role == 'PARENT':

            if children == None:
                raise ValueError(_('Account must be linked with a student account'))
        
        else:
            children = None

        if role == 'STUDENT':
           
            if not id_number:
                raise ValueError(_('ID number is required for a student account'))
          
            if not grade:
                raise ValueError(_('student needs to be in an allocated grade'))
        
        else:
            grade = None
            id_number = None

        if email:
            email = self.normalize_email(email)

        user = self.model(email=email, id_number=id_number, name=name, surname=surname, children=children, phone_number=phone_number, role=role, school=school, **extra_fields)
        user.save(using=self._db)

        return user
        
    
    # user first sign-in activation
    def activate_user(self, email, password):

        # try finding the user using the provided email 
        try:
            user = self.get(email=email)

            # Validate the password
            validate_password(password)

            # Hash and salt the password
            user.set_password(password)
            user.activated = True
        
            # save the updated user to the database
            user.save(using=self._db)
            return user
        
        except self.model.DoesNotExist:
            return "Account with the provided credentials does not exist"
        
        except ValidationError as e:
                return str(e)
        
    # # super user 
    # def create_superuser(self, email, password=None, **extra_fields):

    #     extra_fields.setdefault('is_staff', True)
    #     extra_fields.setdefault('is_superuser', True)
        
    #     if not email:
    #         raise ValueError(_('The Email field must be set'))
        
    #     return self.create_user(email, password=password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    
    # needed feilds 
    email = models.EmailField(_('email address'), unique=True, blank=True, null=True)
    id_number = models.CharField(_('ID number'), max_length=13, unique=True, blank=True, null=True)

    name = models.CharField(_('name'), max_length=32)
    surname = models.CharField(_('surname'), max_length=32)
    phone_number = models.CharField(_('phone number'), max_length=9, unique=True, blank=True, null=True)

    account_id = models.CharField(max_length=15, unique=True)

    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='students', blank=True, null=True)

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    
    activated = models.BooleanField(_('account active or not'), default=False)
    
    # profile picutre
    profile_picture = models.ImageField(upload_to=get_upload_path, blank=True, null=True)
    
    # choices for the role field
    ROLE_CHOICES = [ ('STUDENT', 'Student'), ('TEACHER', 'Teacher'), ('ADMIN', 'Admin'), ('PRINCIPAL', 'Principal'), ('FOUNDER', 'Founder'), ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    
    # children field
    children = models.ManyToManyField('self', blank=True)
    
    # email communication preferance
    event_emails = models.BooleanField(_('email subscription'), default=False)

    # multi-factor authentication
    multifactor_authentication = models.BooleanField(_('multifactor authentication'), default=False)
    
    email_banned = models.BooleanField(_('email banned'), default=False)
    email_ban_amount = models.SmallIntegerField(_('amount of times email has been banned'), default=0)
    
    # permissions needed by django do not change( unless you have a valid reason to )
    is_active = models.BooleanField(_('active'), default=True)
    is_staff = models.BooleanField(_('staff status'), default=False)
    is_superuser = models.BooleanField(_('superuser status'), default=False)
    
    # field for authentication
    USERNAME_FIELD = 'email' 
    
    # all required fields
    REQUIRED_FIELDS = ['name', 'surname', 'role']

    objects = CustomUserManager()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return self.email if self.email else self.id_number

    # overwirte save method for account id generation
    def save(self, *args, **kwargs):
        if not self.account_id:
            self.account_id = self.generate_unique_id('UA')

        super(CustomUser, self).save(*args, **kwargs)

    @staticmethod
    def generate_unique_id(prefix=''):
        max_attempts = 10
        for _ in range(max_attempts):
            unique_part = uuid.uuid4().hex[:13]  # Take only the first 13 characters
            id = f"{prefix}{unique_part}"
            if not CustomUser.objects.filter(account_id=id).exists():
                return id
        raise ValueError('failed to generate a unique account ID after 10 attempts, please try again later.')
            