# celery
from celery import shared_task
from celery.exceptions import Reject

# models
from .models import Classroom
from terms.models import Term

# utility functions
from seeran_backend import utils as system_utilities


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def update_classroom_performance_metrics_task(self, classroom_id, term_id):
    lock_id = f'update_classroom_performance_metrics_task_{classroom_id}'
    if not system_utilities.acquire_lock(lock_id):
        raise Reject('Task is already queued or running')

    try:
        term = Term.objects.get(id=term_id)
        classroom = Classroom.objects.get(id=classroom_id)
        classroom.update_performance_metrics(term.id)
    except Classroom.DoesNotExist:
        # Handle error
        raise Reject('Could not update classroom performance metrics, a classroom in your school with the provided credentials does not exist, please check the classroom details and try again.')
    except Term.DoesNotExist:
        # Handle error
        raise Reject('Could not update classroom performance metrics, a term in your school with the provided credentials does not exist, please check the term details and try again.')
    except Exception as e:
        self.retry(exc=e)
    finally:
        system_utilities.release_lock(lock_id)