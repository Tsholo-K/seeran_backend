# python 
import uuid
import re

# django imports
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models, transaction, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

# utility functions
from authentication.utils import get_upload_path
from accounts import validators as users_validators


class BaseAccountManager(BaseUserManager):
    """
    Custom manager for BaseUser model that handles user creation and activation.

    Methods:
    - create: Creates a new user with the provided details.
    - activate: Activates an existing user account by setting a password and marking the account as activated.
    """
    
    def create(self, email_address=None, name=None, surname=None, role=None, **extra_fields):
        """
        Create and return a new user with the given email, name, surname, and role.
        
        Args:
            email (str): The email address for the new user.
            name (str): The name of the new user.
            surname (str): The surname of the new user.
            role (str): The role of the user (e.g., Teacher, Student).
            **extra_fields: Additional fields for the user model.
        
        Raises:
            ValueError: If name or surname is missing.
            ValidationError: If the specified role is invalid or if an account with the provided email already exists.
        """

        # Normalize email
        email_address = self.normalize_email(email_address) if email_address else None

        # Create user instance
        user = self.model(email_address=email_address, name=name, surname=surname, role=role, **extra_fields)
        user.set_unusable_password()  # User is initially inactive

        # Save the user and handle potential integrity errors
        user.save()
        
        return user

    def activate(self, email_address, password):
        """
        Activate a user account by setting a password and marking it as activated.
        
        Args:
            email (str): The email of the user to activate.
            password (str): The password to set for the user.
        
        Raises:
            ValueError: If the account does not exist or if the password validation fails.
        """

        try:
            account = self.get(email_address=email_address)
            validate_password(password)  # Ensure the password meets the validation criteria

            account.set_password(password)  # Set the password
            account.activated = True  # Mark as activated

            account.save()
            return account
        
        except BaseAccount.DoesNotExist:
            raise ValueError(_('The account with the provided email does not exist. Please check the email and try again.'))

        except ValidationError as e:
            raise ValueError(_(str(e)))

class BaseAccount(AbstractBaseUser, PermissionsMixin):
    """
    Base user model that includes common fields and methods for user accounts.
    
    Attributes:
        ROLE_CHOICES (list): Choices for user roles.
        name (str): User's name.
        surname (str): User's surname.
        email (str): Unique email address for the user.
        role (str): Role of the user in the system (e.g., Teacher, Student).
        activated (bool): Indicates if the account is active.
        profile_picture (ImageField): Optional profile picture for the user.
        multifactor_authentication (bool): Indicates if MFA is enabled.
        email_banned (bool): Indicates if the user's email is banned.
        email_ban_amount (int): Count of how many times the email has been banned.
        is_active (bool): Indicates if the account is active.
        is_staff (bool): Indicates if the user can access the admin site.
        is_superuser (bool): Indicates if the user has all permissions.
        last_updated (datetime): Timestamp of the last update.
        account_id (UUID): Unique identifier for the user account.
    
    Methods:
        clean: Validates user data before saving.
        save: Saves the user instance with validation.
    """

    ROLE_CHOICES = [
        ('FOUNDER', 'Founder'),
        ('PRINCIPAL', 'Principal'),
        ('ADMIN', 'Admin'),
        ('TEACHER', 'Teacher'),
        ('STUDENT', 'Student'),
        ('PARENT', 'Parent'),
    ]
    
    name = models.CharField(_('name'), max_length=64)
    surname = models.CharField(_('surname'), max_length=64)

    email_address = models.EmailField(_('email address'), blank=True, null=True)

    role = models.CharField(choices=ROLE_CHOICES, max_length=16)

    profile_picture = models.ImageField(upload_to=get_upload_path, blank=True, null=True)
    activated = models.BooleanField(_('account active or not'), default=False)

    multifactor_authentication = models.BooleanField(_('multifactor authentication'), default=False)

    email_banned = models.BooleanField(_('email banned'), default=False)
    email_ban_amount = models.SmallIntegerField(_('amount of times email has been banned'), default=0)

    is_active = models.BooleanField(_('active'), default=True)
    is_staff = models.BooleanField(_('staff status'), default=False)
    is_superuser = models.BooleanField(_('superuser status'), default=False)
        
    last_updated = models.DateTimeField(auto_now=True)

    timestamp = models.DateTimeField(auto_now_add=True)
    account_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    USERNAME_FIELD = 'email_address'  # Specifies the field to be used for authentication

    objects = BaseAccountManager()  # Use the custom user manager

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['email_address'], name='unique_account_email_address'),
        ]
        ordering = ['surname', 'name', 'account_id']

    def __str__(self):
        return f'{self.name} {self.surname}'

    def save(self, *args, **kwargs):
        self.clean()
        try:
            super().save(*args, **kwargs)
        except IntegrityError as e:
            error_message = str(e).lower()
            # Handle unique constraint errors gracefully and provide useful feedback.
            if 'unique constraint' in error_message:
                if 'email_address' in error_message:
                    raise ValidationError(_('Could not process your request, an account with the provided email address already exists. Please use a different email address or contact support if you believe this is an error.'))
                elif 'contact_number' in error_message:
                    raise ValidationError(_('The contact number provided is already in use by another account in the system. Please use a unique contact number or verify if the correct number has been entered.'))
                elif 'id_number' in error_message:
                    raise ValidationError(_('Could not process your request, an account with the provided ID number already exists, please use a different ID number.'))
                elif 'passport_number' in error_message:
                    raise ValidationError(_('Could not process your request, an account with the provided passport number already exists, please use a different passport number.'))                
            # If it's not handled, re-raise the original exception
            raise ValidationError(_(error_message))

    def clean(self):
        if self.role not in dict(BaseAccount.ROLE_CHOICES).keys():
            raise ValidationError(_('Could not process your request, the specified account role is invalid. Please choose a valid role from the options: %s.' % [dict(BaseAccount.ROLE_CHOICES).keys()]))

        # validate account email_address
        if self.email_address:
            try:
                validate_email(self.email_address)
            except ValidationError:
                raise ValidationError(_('Could not process your request, the provided email address is not in a valid format. Please correct the email address and try again.'))

            if len(self.email_address) > 254:
                raise ValidationError(_("Could not process your request, email address cannot exceed 254 characters. Please correct the email address and try again."))

        # validate account name and surname
        if not self.name:
            raise ValidationError(_('Could not process your request, a name is required for all accounts on the system. Please provide a valid name.'))
        if not self.surname:
            raise ValidationError(_('Could not process your request, a surname is required for all accounts on the system. Please provide a valid surname.'))
        if len(self.name) > 64:
            raise ValidationError(_("Could not process your request, name cannot exceed 64 characters. Please correct the name and try again."))
        if len(self.surname) > 64:
            raise ValidationError(_("Could not process your request, surname cannot exceed 64 characters. Please correct the surname and try again."))


class Founder(BaseAccount):
    """
    User model representing a Founder in the system.

    Methods:
        clean: Validates founder-specific fields before saving.
        save: Saves the founder instance with validation.
    """
    
    class Meta:
        # Additional metadata options can be defined here
        pass

    def save(self, *args, **kwargs):
        """Override save method to include validation for founder accounts."""
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        """Validate founder-specific fields."""
        super().clean()
        if not self.role == 'FOUNDER':
            raise ValidationError(_('Could not process your request, founder accounts can only have a role of "Founder". Please correct the provided information and try again.'))

        if not self.email_address:
            raise ValidationError(_('Could not process your request, all founder accounts in the system are required to have an email address linked to their account. Please provide a valid email address.'))


class Principal(BaseAccount):
    """
    User model representing a Principal in the system.

    Attributes:
        contact_number (str): Unique contact number for the principal.
        school (ForeignKey): The school associated with the principal.
    
    Methods:
        clean: Validates principal-specific fields before saving.
        save: Saves the principal instance with validation.
    """
    
    contact_number = models.CharField(_('phone number'), max_length=15)
    
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='principal')

    class Meta:
        # A unique constraint that prevents principals from having duplicate contact numbers.
        constraints = [
            models.UniqueConstraint(fields=['contact_number'], name='unique_account_contact_number')
        ]

    def save(self, *args, **kwargs):
        """Override save method to include validation for principal accounts."""
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        """Validate principal-specific fields."""
        super().clean()
        if not self.role == 'PRINCIPAL':
            raise ValidationError(_('Could not process your request, principal accounts can only have a role of "Principal". Please correct the provided information and try again.'))
        if not self.email_address:
            raise ValidationError(_('Could not process your request, all principal accounts in the system are required to have an email address linked to their account. Please provide a valid email address.'))
        
        # Validate contact number
        if not self.contact_number:
            raise ValidationError(_('Could not process your request, all principal accounts in the system are required to have an contact number linked to their account. Please provide a valid contact number.'))
        try:
            if not self.contact_number.isdigit():
                raise ValidationError(_('The contact number provided contains non-numeric characters. Please enter a numeric only contact number (e.g., 0123456789).'))
        except Exception as e:
            raise ValidationError(_(str(e)))
        if len(self.contact_number) < 10 or len(self.contact_number) > 15:
            raise ValidationError(_('The contact number must be between 10 and 15 digits long. Please provide a valid contact number within this range.'))
        
        if not self.school_id:
            raise ValidationError(_('Principal accounts must be associated with a school. Please provide a school for this account.'))


class Admin(BaseAccount):
    """
    User model representing an Admin in the system.

    Attributes:
        school (ForeignKey): The school associated with the admin.
    
    Methods:
        clean: Validates admin-specific fields before saving.
        save: Saves the admin instance with validation.
    """
    
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='admins')

    class Meta:
        # Additional metadata options can be defined here
        pass

    def save(self, *args, **kwargs):
        """Override save method to include validation for admin accounts."""
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        """Validate admin-specific fields."""
        super().clean()
        if not self.role == 'ADMIN':
            raise ValidationError(_('Could not process your request, admin accounts can only have a role of "ADMIN". Please correct the provided information and try again.'))
        if not self.email_address:
            raise ValidationError(_('Could not process your request, all admin accounts in the system are required to have an email address linked to their account. Please provide a valid email address.'))
        if not self.school_id:
            raise ValidationError(_('Could not process your request, admin accounts must be associated with a school. Please provide a school for this account.'))

class Teacher(BaseAccount):
    """
    User model representing a Teacher in the system.

    Attributes:
        school (ForeignKey): The school associated with the teacher.
    
    Methods:
        clean: Validates teacher-specific fields before saving.
        save: Saves the teacher instance with validation.
    """
    
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='teachers')

    class Meta:
        # Additional metadata options can be defined here
        pass

    def save(self, *args, **kwargs):
        """Override save method to include validation for teacher accounts."""
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        """Validate teacher-specific fields."""
        super().clean()
        if not self.role == 'TEACHER':
            raise ValidationError(_('Could not process your request, teacher accounts can only have a role of "TEACHER". Please correct the provided information and try again.'))
        if not self.email_address:
            raise ValidationError(_('Could not process your request, all teacher accounts in the system are required to have an email address linked to their account. Please provide a valid email address.'))
        if not self.school_id:
            raise ValidationError(_('Could not process your request, teacher accounts must be associated with a school. Please provide a school for this account.'))

class Student(BaseAccount):
    """
    User model representing a Student in the system.

    Attributes:
        id_number (str): Unique ID number for the student.
        passport_number (str): Unique passport number for the student.
        event_emails (bool): Indicates if the student is subscribed to event emails.
        grade (ForeignKey): The grade associated with the student.
        school (ForeignKey): The school associated with the student.
    
    Methods:
        clean: Validates student-specific fields before saving.
        save: Saves the student instance with validation.
    """
    
    id_number = models.CharField(_('ID number'), max_length=13, blank=True, null=True)
    passport_number = models.CharField(_('passport number'), max_length=9, blank=True, null=True)

    event_emails_subscription = models.BooleanField(_('email subscription'), default=False)
    
    grade = models.ForeignKey('grades.Grade', on_delete=models.CASCADE, related_name='students')
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='students')

    class Meta:
        # A unique constraint that prevents accounts from having duplicate contact numbers and schools.
        constraints = [
            models.UniqueConstraint(fields=['id_number'], name='unique_account_id_number'),
            models.UniqueConstraint(fields=['passport_number'], name='unique_account_passport_number')
        ]
        ordering = ['surname', 'name', 'account_id']

    def save(self, *args, **kwargs):
        """Override save method to include validation for student accounts."""
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        """Validate student-specific fields."""
        super().clean()
        if not self.role == 'STUDENT':
            raise ValidationError(_('Could not process your request, student accounts can only have a role of "STUDENT". Please correct the provided information and try again.'))
        if not self.school_id:
            raise ValidationError(_('Could not process your request, student accounts must be associated with a school. Please provide a school for this account.'))
        if not self.id_number and not self.passport_number:
            raise ValidationError(_('Could not process your request, either ID or Passport number is required for every student account on the system.'))
        
        if self.id_number and not users_validators.is_valid_south_african_id(self.id_number):
            raise ValidationError(_('The provided ID number is invalid. Please ensure it contains 13 digits, follows the correct date format (YYMMDD), and is a valid South African ID number. If unsure, verify the number and try again.'))
        
        if self.passport_number and not re.match(r'^[A-Za-z0-9]{6,9}$', self.passport_number):
            raise ValidationError(_('The provided passport number is invalid. Please ensure it contains between 6 and 9 alphanumeric characters without spaces or special characters.'))

        # validate grade
        if not self.grade_id:
            raise ValidationError(_('Could not process your request, student accounts must be assigned to a grade. please correct the provided information and try again.'))
        elif self.grade.school != self.school:
            raise ValidationError(_('Could not process your request, the grade the student is getting assigned to must be associated with the school the student is linked to, please correct the provided information and try again'))
        else:
            # Only apply integer checks for numeric grade levels
            try:
                grade_num = int(self.grade.grade)
                if self.school.type == 'PRIMARY' and grade_num > 7:
                    raise ValidationError(_('Could not process your request, primary school students cannot be assigned to grades higher than 7, please correct the provided information and try again'))
                if self.school.type == 'SECONDARY' and grade_num <= 7:
                    raise ValidationError(_('Could not process your request, secondary school students must be assigned to grades higher than 7, please correct the provided information and try again'))
            except ValueError:
                # Handle non-numeric grades like 'R', '00', '000'
                if self.school.type in ['SECONDARY', 'TERTIARY'] and self.grade.grade in ['R', '00', '000']:
                    raise ValidationError(_('Could not process your request, secondary school students must be assigned to grades higher than 7, please correct the provided information and try again'))


class Parent(BaseAccount):
    """
    User model representing a Parent in the system.

    Attributes:
        children (ManyToManyField): Relationship to Student accounts that are children of the parent.
        event_emails (bool): Indicates if the parent is subscribed to event emails.
    
    Methods:
        clean: Validates parent-specific fields before saving.
        save: Saves the parent instance with validation.
    """
    
    children = models.ManyToManyField(Student, blank=True, related_name='parents')

    event_emails_subscription = models.BooleanField(_('email subscription'), default=False)

    class Meta:
        # Additional metadata options can be defined here
        pass

    def save(self, *args, **kwargs):
        """Override save method to include validation for parent accounts."""
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        """Validate parent-specific fields."""
        super().clean()
        if not self.role == 'PARENT':
            raise ValidationError(_('Could not process your request, parent accounts can only have a role of "PARENT". Please correct the provided information and try again.'))
        if not self.email_address:
            raise ValidationError(_('Could not process your request, all parent accounts in the system are required to have an email address linked to their account. Please provide a valid email address.'))

    def add_child(self, child):
        """Custom method to add a child with validation."""
        if child.role != 'STUDENT':
            raise ValidationError(_('Could not process your request, only student accounts can be assigned as children to a parent account.'))

        # If validation passes, add the child
        self.children.add(child)

"""
    Here's a list of some name and surname combinations for dummy data:

        Name: Ethan, Surname: Brooks
        Name: Maya, Surname: Patel
        Name: Liam, Surname: O'Connor
        Name: Sophia, Surname: Zhang
        Name: Noah, Surname: Ali
        Name: Chloe, Surname: Sinclair
        Name: Lucas, Surname: Takahashi
        Name: Ava, Surname: Ndlovu
        Name: Benjamin, Surname: Martinez
        Name: Mia, Surname: Kaur
"""