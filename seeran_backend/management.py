from django.core.management.base import BaseCommand
from django_celery_results.models import TaskResult
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Clean up expired Celery task results'

    def handle(self, *args, **kwargs):
        expire_time = timezone.now() - timedelta(seconds=3600)  # Adjust based on your expiration time
        TaskResult.objects.filter(date_done__lt=expire_time).delete()
        self.stdout.write(self.style.SUCCESS('Successfully cleaned up expired task results'))
