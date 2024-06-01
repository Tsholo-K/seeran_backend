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
            self.class_id = self.generate_unique_id('CR')

        super(Classroom, self).save(*args, **kwargs)

    @staticmethod
    def generate_unique_id(prefix=''):
        max_attempts = 10
     
        for _ in range(max_attempts):
            unique_part = uuid.uuid4().hex[:13]  # Take only the first 13 characters
            id = f"{prefix}{unique_part}"
            if not Classroom.objects.filter(class_id=id).exists():
                return id
      
        raise ValueError('failed to generate a unique classroom ID after 10 attempts, please try again later.')

