# celery
from celery import shared_task
from celery.exceptions import Reject

# django 
from django.apps import apps

# utility functions
from seeran_backend import utils as system_utilities


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def update_term_performance_metrics_task(self, term_performance_id):
    lock_id = f'update_term_performance_metrics_task_{term_performance_id}'
    if not system_utilities.acquire_lock(lock_id):
        raise Reject('Task is already queued or running')

    try:
        # Get the ClassroomPerformance model dynamically
        TermSubjectPerformance = apps.get_model('term_subject_performances', 'TermSubjectPerformance')

        term_performance = TermSubjectPerformance.objects.get(id=term_performance_id)
        term_performance.update_performance_metrics()
    except TermSubjectPerformance.DoesNotExist:
        # Handle error
        raise Reject('an term in your school with the provided credentials does not exist, please check the term details and try again')
    except Exception as e:
        self.retry(exc=e)
    finally:
        system_utilities.release_lock(lock_id)