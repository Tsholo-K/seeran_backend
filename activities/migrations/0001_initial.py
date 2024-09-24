# Generated by Django 5.0 on 2024-09-24 12:18

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('offence', models.CharField(max_length=124, verbose_name='offence')),
                ('details', models.TextField(max_length=1024, verbose_name='more details about the offence')),
                ('date_logged', models.DateTimeField(auto_now_add=True)),
                ('activity_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
            ],
            options={
                'ordering': ['-date_logged'],
            },
        ),
    ]
