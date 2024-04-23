from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import CustomUser
from balances.models import Bill


class Command(BaseCommand):
    help = 'Check for unpaid bills and create bills'

    def handle(self, *args, **options):
        principals = CustomUser.objects.filter(role='PRINCIPAL')
        for principal in principals:
            unpaid_bills = Bill.objects.filter(user=principal, is_paid=False)
            if unpaid_bills:
                # The principal has an unpaid bill
                # Set the in_arears field of the School model to True
                principal.school.in_arears = True
                principal.school.save()
            elif not unpaid_bills and principal.balance.billing_date == timezone.now().date():
                # The principal doesn't have an unpaid bill and today is their billing date
                # Count the number of students in the school
                num_students = CustomUser.objects.filter(role='STUDENT', school=principal.school).count()
                # Create a new bill for this principal
                Bill.objects.create(user=principal, amount=num_students * 20, date_billed=timezone.now().date())

