# python 
import uuid

# django imports
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models, transaction, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

# models
from schools.models import School
from grades.models import Grade

# utility functions
from authentication.utils import get_upload_path


ROLE_CHOICES = [('STUDENT', 'Student'), ('TEACHER', 'Teacher'), ('ADMIN', 'Admin'), ('PRINCIPAL', 'Principal'), ('FOUNDER', 'Founder'), ('PARENT', 'Parent'),]

class BaseUserManager(BaseUserManager):

    @transaction.atomic
    def create(self, email=None, name=None, surname=None, role=None, **extra_fields):
        if not name:
            raise ValueError(_('a name is required for all accounts on the system'))
        
        if not surname:
            raise ValueError(_('a surname is required for all accounts on the system'))
        
        if role not in dict(ROLE_CHOICES).keys():
            raise ValidationError(_('the specified account role is invalid'))

        email = self.normalize_email(email) if email else None

        user = self.model(email=email, name=name, surname=surname, role=role, **extra_fields)

        user.set_unusable_password()

        try:
            user.save(using=self._db)
        except IntegrityError as e:
            # Handle integrity error
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('a account with the provided email address already exists. please use a different email address'))
            else:
                raise
        
        return user

    @transaction.atomic
    def activate(self, email, password):
        try:
            user = self.get(email=email)

            validate_password(password)

            user.set_password(password)
            user.activated = True

            user.save(using=self._db)
            return user
        
        except BaseUser.DoesNotExist:
            raise ValueError("Account with the provided credentials does not exist")
        
        except ValidationError as e:
            raise ValueError(str(e).lower())


class BaseUser(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(_('name'), max_length=64)
    surname = models.CharField(_('surname'), max_length=64)

    email = models.EmailField(_('email address'), unique=True, blank=True, null=True)

    role = models.CharField(choices=ROLE_CHOICES)

    activated = models.BooleanField(_('account active or not'), default=False)
    profile_picture = models.ImageField(upload_to=get_upload_path, blank=True, null=True)

    multifactor_authentication = models.BooleanField(_('multifactor authentication'), default=False)

    email_banned = models.BooleanField(_('email banned'), default=False)
    email_ban_amount = models.SmallIntegerField(_('amount of times email has been banned'), default=0)

    is_active = models.BooleanField(_('active'), default=True)
    is_staff = models.BooleanField(_('staff status'), default=False)
    is_superuser = models.BooleanField(_('superuser status'), default=False)
    
    account_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    USERNAME_FIELD = 'email'

    objects = BaseUserManager()

    class Meta:
        ordering = ['surname', 'name', 'account_id']

    def __str__(self):
        return f'{self.name} {self.surname}'

    def clean(self):
        if self.email:
            try:
                validate_email(self.email)

            except ValidationError:
                raise ValidationError(_('the provided email address is not in a valid format. please correct the email address and try again'))
            
            if len(self.email) > 254:
                raise ValidationError(_("email address cannot exceed 254 characters. please correct the email address and try again"))
            
        if len(self.name) > 64:
            raise ValidationError(_("name cannot exceed 64 characters. please correct the name and try again"))
        
        if len(self.surname) > 64:
            raise ValidationError(_("surname cannot exceed 64 characters. please correct the surname and try again"))
        
    def save(self, *args, **kwargs):
        try:
            super().save(*args, **kwargs)

        except IntegrityError as e:
            # Handle unique constraint violation on the email field
            if 'unique constraint' in str(e).lower() and 'email' in str(e).lower():
                raise ValidationError(_('An account with the provided email address already exists. Please use a different email address.'))
            else:
                raise e  # Re-raise the exception if it's a different IntegrityError


class Founder(BaseUser):

    class Meta:
        ...

    def clean(self):
        super().clean()

        if not self.role == 'FOUNDER':
            raise ValidationError(_('could not proccess your request, founder accounts can only have a role of \'Founder\'. please correct the provided information and try again'))

        if not self.email:
            raise ValidationError(_('all founder accounts in the system are required to have an email address linked to their account. please correct the provided information and try again'))

    def save(self, *args, **kwargs):
        self.full_clean()
        
        try:
            super().save(*args, **kwargs)

        except IntegrityError as e:
            # Handle integrity error
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('an account with the provided email address already exists. please use a different email address'))
            
            else:
                raise


class Principal(BaseUser):
    contact_number = models.CharField(_('phone number'), max_length=15, unique=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='principal')

    class Meta:
        ...

    def clean(self):
        super().clean()

        if not self.role == 'PRINCIPAL':
            raise ValidationError(_('could not proccess your request, principal accounts can only have a role of \'Principal\'. please correct the provided information and try again'))

        if not self.email:
            raise ValidationError(_('all principal accounts in the system are required to have an email address linked to their account. please correct the provided information and try again'))

        if not self.contact_number.isdigit():
            raise ValidationError(_('contact number should only contain digits. please correct the contact number and try again'))
        
        if not (10 <= len(self.contact_number) <= 15):
            raise ValidationError(_('contact number should be between 10 and 15 digits. please correct the contact number and try again'))
        
        if not self.school:
            raise ValidationError(_('principal accounts must be associated with a school. please correct the provided information and try again'))

    def save(self, *args, **kwargs):
        self.full_clean()
        
        try:
            super().save(*args, **kwargs)

        except IntegrityError as e:
            error_message = str(e).lower()
            if 'unique constraint' in error_message:
                if 'contact_number' in error_message:
                    raise ValidationError(_('an account with the provided contact number already exists. Please use a different contact number.'))
                
                elif 'email' in error_message:
                    raise ValidationError(_('an account with the provided email address already exists. Please use a different email address.'))
                
                else:
                    raise ValidationError(_('A unique constraint was violated. Please check the data and try again.'))
            else:
                raise


class Admin(BaseUser):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='admins')

    class Meta:
        ...

    def clean(self):
        super().clean()

        if not self.role == 'ADMIN':
            raise ValidationError(_('could not proccess your request, admin accounts can only have a role of \'Admin\'. please correct the provided information and try again'))

        if not self.email:
            raise ValidationError(_('all admin accounts in the system are required to have an email address linked to their account. please correct the provided information and try again'))

        if not self.school:
            raise ValidationError(_('admin accounts must be associated with a school. please correct the provided information and try again'))

    def save(self, *args, **kwargs):
        self.full_clean()
        
        try:
            super().save(*args, **kwargs)

        except IntegrityError as e:
            # Handle integrity error
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('an account with the provided email address already exists. please use a different email address'))
            
            else:
                raise


class Student(BaseUser):
    id_number = models.CharField(_('ID number'), max_length=13, unique=True, blank=True, null=True)
    passport_number = models.CharField(_('passport number'), max_length=9, unique=True, blank=True, null=True)

    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='students')

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='students')

    event_emails = models.BooleanField(_('email subscription'), default=False)

    class Meta:
        ...

    def clean(self):
        super().clean()

        if not self.role == 'STUDENT':
            raise ValidationError(_('could not proccess your request, student accounts can only have a role of \'Student\'. please correct the provided information and try again'))

        if not self.id_number and not self.passport_number:
            raise ValidationError(_('either ID or Passport number is required for every student account on the system'))
        
        if self.school and self.grade.school != self.school:
            raise ValidationError(_('the grade the student is getting assigned to must be associated with the school the student is linked to'))
        
        if self.school.type == 'PRIMARY' and int(self.grade.grade) > 7:
            raise ValidationError(_('primary school students cannot be assigned to grades higher than 7, please correct the provided information and try again'))
        
        if self.school.type == 'SECONDARY' and int(self.grade.grade) <= 7:
            raise ValidationError(_('secondary school students must be assigned to grades higher than 7, please correct the provided information and try again'))

    def save(self, *args, **kwargs):
        self.full_clean()
        
        try:
            super().save(*args, **kwargs)

        except IntegrityError as e:
            error_message = str(e).lower()
            if 'unique constraint' in error_message:
                if 'id_number' in error_message:
                    raise ValidationError(_('An account with the provided ID number already exists, please use a different ID number.'))
                
                elif 'passport_number' in error_message:
                    raise ValidationError(_('An account with the provided passport number already exists, please use a different passport number.'))
                
                elif 'email' in error_message:
                    raise ValidationError(_('an account with the provided email address already exists, please use a different email address.'))

                else:
                    raise ValidationError(_('A unique constraint was violated, please check the provided information and try again.'))
            else:
                raise


class Parent(BaseUser):
    children = models.ManyToManyField(Student, blank=True, related_name='parents')

    event_emails = models.BooleanField(_('email subscription'), default=False)

    class Meta:
        ...

    def clean(self):
        super().clean()

        if not self.role == 'PARENT':
            raise ValidationError(_('could not proccess your request, parent accounts can only have a role of \'Parent\'. please correct the provided information and try again'))

        if not self.email:
            raise ValidationError(_('all parent accounts in the system are required to have an email address linked to their account. please correct the provided information and try again'))

        if self.children.exists():
            if any(child.role != 'STUDENT' for child in self.children.all()):
                raise ValidationError(_('only student accounts can be assigned as children'))
            
            if self in self.children.all():
                raise ValidationError(_('an account cannot be it\'s own parent'))

    def save(self, *args, **kwargs):
        self.full_clean()
        
        try:
            super().save(*args, **kwargs)

        except IntegrityError as e:
            # Handle integrity error
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('an account with the provided email address already exists. please use a different email address'))
            
            else:
                raise


class Teacher(BaseUser):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='teachers')

    class Meta:
        ...

    def clean(self):
        super().clean()

        if not self.role == 'TEACHER':
            raise ValidationError(_('could not proccess your request, teacher accounts can only have a role of \'Teacher\'. please correct the provided information and try again'))

        if not self.email:
            raise ValidationError(_('all teacher accounts in the system are required to have an email address linked to their account. please correct the provided information and try again'))
        
        if not self.school:
            raise ValidationError(_('teacher accounts must be associated with a school. please correct the provided information and try again'))

    def save(self, *args, **kwargs):
        self.full_clean()
        
        try:
            super().save(*args, **kwargs)

        except IntegrityError as e:
            # Handle integrity error
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('an account with the provided email address already exists. please use a different email address'))
            
            else:
                raise










































































# class CustomUserManager(BaseUserManager):
#     """
#     Custom manager for the CustomUser model.
#     Provides methods for creating users and activating accounts.
#     """

#     @transaction.atomic
#     def create_user(self, email=None, id_number=None, passport_number=None, name=None, surname=None, contact_number=None, role=None, school=None, grade=None, **extra_fields):
#         """
#         Creates and saves a user with the given parameters.

#         Args:
#             email (str): Email address of the user.
#             id_number (str): ID number of the user.
#             passport_number (str): Passport number of the user.
#             name (str): First name of the user.
#             surname (str): Last name of the user.
#             phone_number (str): Phone number of the user.
#             role (str): Role of the user ('STUDENT', 'TEACHER', 'ADMIN', 'PRINCIPAL', 'FOUNDER', 'PARENT').
#             school (School): School associated with the user (required for 'STUDENT', 'TEACHER', 'ADMIN', 'PRINCIPAL').
#             grade (Grade): Grade associated with the user (required for 'STUDENT').
#             **extra_fields: Additional fields to save.

#         Returns:
#             CustomUser: Created user instance.

#         Raises:
#             ValueError: If required fields are not provided or if validation fails.
#         """

#         # Ensure at least one identifier (email, ID number, passport number) is provided
#         if not email and not id_number and not passport_number:
#             raise ValueError(_('either email, ID number or Passport number must be provided for the creation of an account depandant on role'))
        
#         # Ensure name and surname are provided
#         if not name:
#             raise ValueError(_('invalid information provided, account missing name. all accounts are required to have a name associated with them no matter the role'))
#         if not surname:
#             raise ValueError(_('invalid information provided, account missing surname. all accounts are required to have a surname associated with them no matter the role'))

#         # # Ensure country is provided will be implemeneted later on
#         # if not country:
#         #     raise ValueError(_('invalid information provided, account missing country. all accounts are required to have a country associated with them no matter the role'))

#         # Check if the email already exists
#         if email:
#             try:
#                 validate_email(email)
#             except ValidationError:
#                 raise ValidationError(_('the provided email address is invalid'))

            
#             if self.model.objects.filter(email=email).exists():
#                 raise ValueError(_('an account with the provided email address already exists'))
            
#             email = self.normalize_email(email)

#         # Check if the ID number already exists
#         if id_number and self.model.objects.filter(id_number=id_number).exists():
#             raise ValueError(_('an account with the provided ID number already exists'))
        
#         # Check if the passport number already exists
#         if passport_number and self.model.objects.filter(passport_number=passport_number).exists():
#             raise ValueError(_('an account with the provided Passport number already exists'))

#         # Validate role
#         if role not in ['FOUNDER', 'PARENT', 'STUDENT', 'TEACHER', 'ADMIN', 'PRINCIPAL']:
#             raise ValueError(_('the role specified for the account is invalid'))

#         # Validate role-specific requirements
#         if role in ['STUDENT', 'TEACHER', 'ADMIN', 'PRINCIPAL']:
#             if school is None:
#                 raise ValueError(_('the role specified for the account requires that the account be associated with a school'))
#         else:
#             school = None  # Parents/founders should not be associated with a school

#         # Validate requirements for specific roles
#         if role == 'PRINCIPAL':
#             if contact_number is None:
#                 raise ValueError(_('account must have a contact number'))
#             if not contact_number.isdigit():
#                 raise ValidationError(_('contact number should contain only digits'))
#             if len(contact_number) < 10 or len(contact_number) > 15:
#                 raise ValidationError(_('contact number should be between 10 and 15 digits'))
#         else:
#             contact_number = None

#         if role == 'STUDENT':
#             if not id_number and not passport_number:
#                 raise ValueError(_('Either ID or Passport number is required for a student account'))
            
#             if id_number:
#                 passport_number = None
#             else:
#                 id_number = None
            
#             if not grade:
#                 raise ValueError(_('Student needs to be allocated to a grade'))
            
#             if email == '':
#                 email = None
#         else:
#             grade = None
#             passport_number = None
#             id_number = None

#         # Create and save user instance
#         user = self.model(email=email, id_number=id_number, passport_number=passport_number, name=name, surname=surname, grade=grade, contact_number=contact_number, role=role, school=school, **extra_fields)
#         user.set_unusable_password()  # Set unusable password until activated
#         user.save(using=self._db)

#         return user

#     @transaction.atomic
#     def activate_user(self, email, password):
#         """
#         Activates a user account with the provided email and sets a password.

#         Args:
#             email (str): Email address of the user.
#             password (str): Password to set for the user.

#         Returns:
#             CustomUser: Activated user instance.

#         Raises:
#             ValueError: If the user account does not exist or if password validation fails.
#         """

#         try:
#             user = self.get(email=email)

#             # Validate the password
#             validate_password(password)

#             # Hash and salt the password
#             user.set_password(password)
#             user.activated = True

#             # Save the updated user to the database
#             user.save(using=self._db)
#             return user

#         except self.model.DoesNotExist:
#             raise ValueError("Account with the provided credentials does not exist")

#         except ValidationError as e:
#             raise ValueError(str(e).lower())


# class CustomUser(AbstractBaseUser, PermissionsMixin):
#     """
#     Custom user model representing users of the application.
#     """

#     email = models.EmailField(_('email address'), unique=True, blank=True, null=True)
#     id_number = models.CharField(_('ID number'), max_length=13, unique=True, blank=True, null=True)
#     passport_number = models.CharField(_('passport number'), max_length=9, unique=True, blank=True, null=True)

#     name = models.CharField(_('name'), max_length=64)
#     surname = models.CharField(_('surname'), max_length=64)
    
#     contact_number = models.CharField(_('phone number'), max_length=15, unique=True, blank=True, null=True)

#     grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='students', blank=True, null=True)
#     school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='users', blank=True, null=True)
    
#     activated = models.BooleanField(_('account active or not'), default=False)
#     profile_picture = models.ImageField(upload_to=get_upload_path, blank=True, null=True)

#     children = models.ManyToManyField('self', blank=True)
#     event_emails = models.BooleanField(_('email subscription'), default=False)
#     multifactor_authentication = models.BooleanField(_('multifactor authentication'), default=False)
#     email_banned = models.BooleanField(_('email banned'), default=False)
#     email_ban_amount = models.SmallIntegerField(_('amount of times email has been banned'), default=0)

#     is_active = models.BooleanField(_('active'), default=True)
#     is_staff = models.BooleanField(_('staff status'), default=False)
#     is_superuser = models.BooleanField(_('superuser status'), default=False)

#     role = models.CharField(choices=ROLE_CHOICES)

#     account_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

#     USERNAME_FIELD = 'email'
#     REQUIRED_FIELDS = ['name', 'surname', 'role']

#     objects = CustomUserManager()

#     class Meta:
#         ordering = ['surname', 'name', 'account_id']
#         unique_together = ('name', 'surname', 'id_number')
#         indexes = [
#             models.Index(fields=['role']),
#             models.Index(fields=['grade', 'school']),
#         ]

#     def __str__(self):
#         return self.name + ' ' + self.surname
        
#     def clean(self):
#         # Role validation
#         if self.role not in dict(ROLE_CHOICES).keys():
#             raise ValidationError(_('the role specified for the account is invalid'))

#         # Email validation
#         if self.email:
#             try:
#                 validate_email(self.email)
#             except ValidationError:
#                 raise ValidationError(_('the provided email address is not in a valid format. please correct the email address and try again'))
#             if len(self.email) > 254:
#                 raise ValidationError(_("email address cannot exceed 254 characters"))

#         # ID number and passport number validation
#         if self.id_number and len(self.id_number) > 13:
#             raise ValidationError(_("ID number cannot exceed 13 characters"))
#         if self.passport_number and len(self.passport_number) > 9:
#             raise ValidationError(_("passport number cannot exceed 9 characters"))

#         # Name and surname validation
#         if len(self.name) > 64:
#             raise ValidationError(_("name cannot exceed 64 characters"))
#         if len(self.surname) > 64:
#             raise ValidationError(_("surname cannot exceed 64 characters"))

#         # Contact number validation
#         if self.contact_number:
#             if self.role != 'PRINCIPAL':
#                 raise ValidationError(_('only principal accounts can contain contact numbers'))
#             if not self.contact_number.isdigit():
#                 raise ValidationError(_('contact number should contain only digits'))
#             if not (10 <= len(self.contact_number) <= 15):
#                 raise ValidationError(_('contact number should be between 10 and 15 digits'))

#         # Grade validation
#         if self.role == 'STUDENT':
#             if not self.grade:
#                 raise ValidationError(_('student accounts need to be allocated to a grade'))
#             if self.school and self.grade.school != self.school:
#                 raise ValidationError(_('the grade must be associated with the school the student account is linked to'))
#             if self.school.type == 'PRIMARY' and int(self.grade.grade) > 7:
#                 raise ValidationError(_('primary school students cannot be assigned to grades higher than 7'))
#             if self.school.type == 'SECONDARY' and int(self.grade.grade) <= 7:
#                 raise ValidationError(_('secondary school students must be assigned to grades higher than 7'))
#         elif self.role in ['PARENT', 'FOUNDER', 'PRINCIPAL', 'TEACHER', 'ADMIN']:
#             if self.grade is not None:
#                 raise ValidationError(_('only student accounts can be associated with a grade'))

#         # Children validation
#         if self.pk:
#             if self.role != 'PARENT':
#                 if self.children.exists():
#                     raise ValidationError(_('only parent accounts can be assigned children'))
#             elif self.role == 'PARENT':
#                 if self.children.exists():
#                     if any(child.role != 'STUDENT' for child in self.children.all()):
#                         raise ValidationError(_('only student accounts can be assigned as children'))
#                     if self in self.children.all():
#                         raise ValidationError(_('an account cannot be their own parent'))
                
#     def save(self, *args, **kwargs):
#         """
#         indicates whether the model instance is being created (i.e., it is a new instance that has not yet been saved to the database)
#         or updated (i.e., it already exists in the database and is being modified)
#         """
#         self.clean()

#         try:
#             super().save(*args, **kwargs)
#         except Exception as e:
#             raise ValidationError(_(str(e).lower()))
            