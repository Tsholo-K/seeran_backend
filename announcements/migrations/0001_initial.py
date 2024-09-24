# Generated by Django 5.0 on 2024-09-24 12:18

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('announced_at', models.DateTimeField(auto_now_add=True, help_text='Time when the announcement was made')),
                ('title', models.CharField(help_text='Title of the announcement', max_length=124)),
                ('message', models.TextField(help_text='Message of the announcement', max_length=1024)),
                ('announcement_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
            ],
            options={
                'ordering': ['-announced_at'],
            },
        ),
    ]