# Generated by Django 5.0 on 2024-09-24 12:18

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('student_group_timetables', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentgrouptimetable',
            name='subscribers',
            field=models.ManyToManyField(related_name='timetables', to='users.student'),
        ),
    ]