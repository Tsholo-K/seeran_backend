# django imports
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

# python 
import uuid

# models
from schools.models import School
from grades.models import Grade

# utility functions
from authentication.utils import get_upload_path, is_phone_number_valid, validate_user_email


ROLE_CHOICES = [
    ('STUDENT', 'Student'),
    ('TEACHER', 'Teacher'),
    ('ADMIN', 'Admin'),
    ('PRINCIPAL', 'Principal'),
    ('FOUNDER', 'Founder'),
    ('PARENT', 'Parent'),
]

class CustomUserManager(BaseUserManager):
    """
    Custom manager for the CustomUser model.
    Provides methods for creating users and activating accounts.
    """


    @transaction.atomic
    def create_user(self, email=None, id_number=None, passport_number=None, name=None, surname=None, phone_number=None, role=None, school=None, grade=None, **extra_fields):
        """
        Creates and saves a user with the given parameters.

        Args:
            email (str): Email address of the user.
            id_number (str): ID number of the user.
            passport_number (str): Passport number of the user.
            name (str): First name of the user.
            surname (str): Last name of the user.
            phone_number (str): Phone number of the user.
            role (str): Role of the user ('STUDENT', 'TEACHER', 'ADMIN', 'PRINCIPAL', 'FOUNDER', 'PARENT').
            school (School): School associated with the user (required for 'STUDENT', 'TEACHER', 'ADMIN', 'PRINCIPAL').
            grade (Grade): Grade associated with the user (required for 'STUDENT').
            **extra_fields: Additional fields to save.

        Returns:
            CustomUser: Created user instance.

        Raises:
            ValueError: If required fields are not provided or if validation fails.
        """

        # Ensure at least one identifier (email, ID number, passport number) is provided
        if not email and not id_number and not passport_number:
            raise ValueError(_('either email, ID number or Passport number must be provided for the creation of an account depandant on role'))
        
        # Ensure name and surname are provided
        if not name:
            raise ValueError(_('invalid information provided, account missing name. all accounts are required to have a name associated with them no matter the role'))
        if not surname:
            raise ValueError(_('invalid information provided, account missing surname. all accounts are required to have a surname associated with them no matter the role'))

        # Check if the email already exists
        if email:
            if not validate_user_email(email):
                raise ValueError(_('invalid email address'))
            
            if self.model.objects.filter(email=email).exists():
                raise ValueError(_('an account with the provided email address already exists'))
            
            email = self.normalize_email(email)

        # Check if the ID number already exists
        if id_number and self.model.objects.filter(id_number=id_number).exists():
            raise ValueError(_('an account with the provided ID number already exists'))
        
        # Check if the passport number already exists
        if passport_number and self.model.objects.filter(passport_number=passport_number).exists():
            raise ValueError(_('an account with the provided Passport number already exists'))

        # Validate role-specific requirements
        if role in ['STUDENT', 'TEACHER', 'ADMIN', 'PRINCIPAL']:
            if school is None:
                raise ValueError(_('the role specified for the account requires that the account be associated with a school'))
        else:
            school = None  # Parents/founders should not be associated with a school

        # Validate requirements for specific roles
        if role == 'PRINCIPAL':
            if phone_number is None:
                raise ValueError(_('Account must have a contact number'))
            if not is_phone_number_valid(phone_number):
                raise ValueError(_('Invalid phone number format'))
        else:
            phone_number = None

        if role == 'STUDENT':
            if not id_number and not passport_number:
                raise ValueError(_('Either ID or Passport number is required for a student account'))
            
            if id_number:
                passport_number = None
            else:
                id_number = None
            
            if not grade:
                raise ValueError(_('Student needs to be allocated to a grade'))
            
            if email == '':
                email = None
        else:
            grade = None
            passport_number = None
            id_number = None

        # Create and save user instance
        user = self.model(email=email, id_number=id_number, passport_number=passport_number, name=name, surname=surname, grade=grade, phone_number=phone_number, role=role, school=school, **extra_fields)
        user.set_unusable_password()  # Set unusable password until activated
        user.save(using=self._db)

        return user

    @transaction.atomic
    def activate_user(self, email, password):
        """
        Activates a user account with the provided email and sets a password.

        Args:
            email (str): Email address of the user.
            password (str): Password to set for the user.

        Returns:
            CustomUser: Activated user instance.

        Raises:
            ValueError: If the user account does not exist or if password validation fails.
        """

        try:
            user = self.get(email=email)

            # Validate the password
            validate_password(password)

            # Hash and salt the password
            user.set_password(password)
            user.activated = True

            # Save the updated user to the database
            user.save(using=self._db)
            return user

        except self.model.DoesNotExist:
            raise ValueError("Account with the provided credentials does not exist")

        except ValidationError as e:
            raise ValueError(str(e))


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model representing users of the application.
    """

    email = models.EmailField(_('email address'), unique=True, blank=True, null=True)
    id_number = models.CharField(_('ID number'), max_length=13, unique=True, blank=True, null=True)
    passport_number = models.CharField(_('passport number'), max_length=9, unique=True, blank=True, null=True)

    name = models.CharField(_('name'), max_length=64)
    surname = models.CharField(_('surname'), max_length=64)
    phone_number = models.CharField(_('phone number'), max_length=9, unique=True, blank=True, null=True)

    account_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='students', blank=True, null=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='users', blank=True, null=True)
    
    activated = models.BooleanField(_('account active or not'), default=False)
    profile_picture = models.ImageField(upload_to=get_upload_path, blank=True, null=True)

    role = models.CharField(choices=ROLE_CHOICES)

    children = models.ManyToManyField('self', blank=True)
    event_emails = models.BooleanField(_('email subscription'), default=False)
    multifactor_authentication = models.BooleanField(_('multifactor authentication'), default=False)
    email_banned = models.BooleanField(_('email banned'), default=False)
    email_ban_amount = models.SmallIntegerField(_('amount of times email has been banned'), default=0)

    is_active = models.BooleanField(_('active'), default=True)
    is_staff = models.BooleanField(_('staff status'), default=False)
    is_superuser = models.BooleanField(_('superuser status'), default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'surname', 'role']

    objects = CustomUserManager()

    class Meta:
        ordering = ['surname', 'name', 'account_id']

    def __str__(self):
        return self.name + ' ' + self.surname

    def clean(self):
        if self.email and len(self.email) > 254:
            raise ValidationError("email address cannot exceed 254 characters")
        if len(self.name) > 64:
            raise ValidationError("name cannot exceed 64 characters")
        if len(self.surname) > 64:
            raise ValidationError("surname cannot exceed 64 characters")
        if self.id_number and len(self.id_number) > 13:
            raise ValidationError("ID number cannot exceed 13 characters")
        if self.passport_number and len(self.passport_number) > 9:
            raise ValidationError("passport number cannot exceed 9 characters")

    def save(self, *args, **kwargs):
        # Call clean to validate fields
        self.clean()
        super().save(*args, **kwargs)
            