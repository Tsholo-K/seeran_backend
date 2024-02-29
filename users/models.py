from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from grades.models import Grades


class StudentManager(BaseUserManager):
    def create_user(self, email, password=None):
        if not email:
            raise ValueError('Users must have an email address')
        user = self.model(
            email=self.normalize_email(email),
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

class Student(AbstractBaseUser):
    email = models.EmailField(unique=True,)
    phone_number = PhoneNumberField(region='ZA')
    password = models.CharField(max_length=128)
    grades = models.ForeignKey(Grades, on_delete=models.PROTECT, default=None, null=True)
    parent = models.ForeignKey('Parent', on_delete=models.PROTECT )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = StudentManager()

    USERNAME_FIELD = 'email'

    def __str__(self):
        return self.email


class Parent(AbstractBaseUser):
    ...