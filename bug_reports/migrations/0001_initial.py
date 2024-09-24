# Generated by Django 5.0 on 2024-09-24 12:18

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BugReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('section', models.CharField(max_length=124)),
                ('dashboard', models.CharField(choices=[('STUDENT', 'Student'), ('TEACHER', 'Teacher'), ('ADMIN', 'Admin'), ('PRINCIPAL', 'Principal')], max_length=10)),
                ('description', models.TextField(max_length=1024)),
                ('status', models.CharField(choices=[('NEW', 'New'), ('IN_PROGRESS', 'In Progress'), ('RESOLVED', 'Resolved')], default='NEW', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('bugreport_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
            ],
        ),
    ]
