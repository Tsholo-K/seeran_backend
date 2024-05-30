# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db import IntegrityError

# models
from users.models import CustomUser
from schools.models import School
from grades.models import Grade, Subject


class Classroom(models.Model):

    room_number = models.CharField(_('classroom number'), max_length=6)

    teacher = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING, related_name='taught_classes')
    students = models.ManyToManyField(CustomUser, related_name='enrolled_classes')
    parents = models.ManyToManyField(CustomUser, related_name='children_classes')

    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='grade_classes')

    register_class = models.BooleanField(_('is the class a register class'), default=False)
    
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='subject_classes', null=True, blank=True)
    group = models.CharField(_('class group'), max_length=10)

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='classes')

    # class account id 
    class_id = models.CharField(_('classroom identifier'), max_length=15, unique=True)

    class Meta:
        verbose_name = _('classroom')
        verbose_name_plural = _('classrooms')

    def __str__(self):
        return self.name

    # class account id creation handler
    def save(self, *args, **kwargs):
        if not self.class_id:
            self.class_id = self.generate_unique_account_id('CR')

        attempts = 0
        while attempts < 5:
            try:
                super().save(*args, **kwargs)
                break
            except IntegrityError:
                self.class_id = self.generate_unique_account_id('CR') # Class Room
                attempts += 1
        if attempts >= 5:
            raise ValueError('Could not create class with unique account ID after 5 attempts. Please try again later.')

    @staticmethod
    def generate_unique_account_id(prefix=''):
        while True:
            unique_part = uuid.uuid4().hex
            account_id = prefix + unique_part
            account_id = account_id[:15].ljust(15, '0')

            if not Classroom.objects.filter(class_id=account_id).exists():
                return account_id

