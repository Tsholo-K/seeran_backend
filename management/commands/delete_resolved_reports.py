from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from bugreports.models import BugReport


class Command(BaseCommand):
    help = 'Delete bug reports that have been resolved for a month'

    def handle(self, *args, **kwargs):
        one_month_ago = timezone.now() - timedelta(days=30)
        BugReport.objects.filter(status="RESOLVED", updated_at__lte=one_month_ago).delete()
        self.stdout.write('Bug reports deleted successfully.')
