from django.core.management.base import BaseCommand
from django.utils import timezone
from schools.models import School
from balances.models import Bill

class Command(BaseCommand):
    help = 'Check compliance of schools'

    def handle(self, *args, **options):
        schools = School.objects.all()
        for school in schools:
            # Get the date 7 days ago
            seven_days_ago = timezone.now().date() - timezone.timedelta(days=7)
            # Check if the school has been in arrears for 7 days
            if school.in_arears and school.balance.last_updated.date() <= seven_days_ago:
                # Set the none_compliant field to True
                school.none_compliant = True
                school.save()
