from decimal import Decimal
from dateutil.relativedelta import relativedelta

# django
from django.db import transaction
from django.utils import timezone

# celery
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

# models
from .models import Balance
from accounts.models import BaseAccount
from invoices.models import Invoice


@shared_task(bind=True, max_retries=3)
def bill_single_user(self, user_id):

    try:
        # Get the user associated with the task
        user = BaseAccount.objects.get(pk=user_id)

        # Check if a bill already exists for this user for this month
        existing_bill = Invoice.objects.filter(user=user, date_billed__year=today.year, date_billed__month=today.month).first()
        
        if existing_bill is not None:
            # If a bill already exists, skip the billing proccess
            return None
        
        # Your API call to bill the user goes here
        # This is just a placeholder
        api_result = 0 # bill_user_api_call(user)
        
        # Get today's date
        today = timezone.now().date()
        
        # Check the result of the API call
        if api_result.status_code == 200:

            with transaction.atomic():

                # If the API call was successful, create a new Bill instance
                Invoice.objects.create(
                    user=user,
                    student=api_result.student,
                    reason=api_result.reason,
                    school=api_result.school,
                    amount=Decimal(api_result.amount),
                    date_billed=today,
                    is_paid=True,
                    bill_id=api_result.bill_id,
                )
                
                # Update the billing_date in the user's Balance
                balance = Balance.objects.get(user=user)
                balance.billing_date = today.replace(day=1) + relativedelta(months=1)
                balance.save()

        else:
            # If the API call was not successful, handle the error
            # This could involve creating a Bill instance with is_paid=False,
            # or retrying the billing operation at a later time
            with transaction.atomic():

                # If the API call was successful, create a new Bill instance
                Invoice.objects.create(
                    user=user,
                    student=api_result.student,
                    reason=api_result.reason,
                    school=api_result.school,
                    amount=Decimal(api_result.amount),
                    date_billed=today,
                    is_paid=False,
                    bill_id=api_result.bill_id,
                )
                
                # Update the billing_date in the user's Balance
                balance = Balance.objects.get(user=user)
                balance.billing_date = today.replace(day=1) + relativedelta(months=1)
                balance.save()

    except BaseUser.DoesNotExist:
        return None # log the error log_error(f"User with id {user_id} does not exist.")

    except Exception as e:
        # If a temporary error occurs, retry the task
        try:
            raise self.retry(exc=e, countdown=60*30)  # Retry in 30 minutes
        
        except MaxRetriesExceededError:
            # If the maximum number of retries has been exceeded, log the error
            return None #log the error log_error(f"User with id {user_id} does not exist.")


@shared_task
def bill_users():

    # Get today's date
    today = timezone.now().date()

    # Get all balances that have their billing date today
    balances = Balance.objects.filter(billing_date=today)

    # Iterate over the balances
    for balance in balances:
        # Get the user associated with the balance
        user = balance.user
        
        # Check if a bill already exists for this user for this month
        existing_bill = Invoice.objects.filter(user=user, date_billed__year=today.year, date_billed__month=today.month).first()
        
        if existing_bill is not None:
            # If a bill already exists, skip this user
            continue

        # Your API call to bill the user goes here
        # This is just a placeholder
        api_result = 0 # bill_user_api_call(user)

        # Check the result of the API call
        if api_result.status_code == 200:
            
            with transaction.atomic():

                # If the API call was successful, create a new Bill instance
                Invoice.objects.create(
                    user=user,
                    student=api_result.student,
                    reason=api_result.reason,
                    school=api_result.school,
                    amount=Decimal(api_result.amount),
                    date_billed=today,
                    is_paid=True,
                    bill_id=api_result.bill_id,
                )
                
                # Update the billing_date in the user's Balance
                balance = Balance.objects.get(user=user)
                balance.billing_date = today.replace(day=1) + relativedelta(months=1)
                balance.save()
                            
        else:
            # If the API call was not successful, handle the error
            # This could involve creating a Bill instance with is_paid=False,
            # or retrying the billing operation at a later time
            bill_single_user.apply_async(args=[user.id], countdown=60*30)
