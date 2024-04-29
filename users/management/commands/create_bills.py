from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import CustomUser
from balances.models import Bill
from django.db import transaction


class Command(BaseCommand):
    help = 'Check for unpaid bills and create bills'

    def handle(self, *args, **options):
        principals = CustomUser.objects.filter(role='PRINCIPAL').select_related('school')
        for principal in principals:
            unpaid_bills = Bill.objects.filter(user=principal, is_paid=False)
            if unpaid_bills:
                principal.school.in_arears = True
            else:
                principal.school.in_arears = False
                if principal.balance.billing_date == timezone.now().date():
                    num_students = CustomUser.objects.filter(role='STUDENT', school=principal.school).count()
                    with transaction.atomic():
                        Bill.objects.create(user=principal, amount=num_students * 20, date_billed=timezone.now().date())
        principal.school.save()


