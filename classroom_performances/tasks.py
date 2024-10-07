# celery
from celery import shared_task
from celery.exceptions import Reject

# django 
from django.apps import apps

# utility functions
from seeran_backend import utils as system_utilities


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def update_classroom_performance_metrics_task(self, classroom_performance_id):
    lock_id = f'update_classroom_performance_metrics_task_{classroom_performance_id}'
    if not system_utilities.acquire_lock(lock_id):
        raise Reject('Task is already queued or running')

    try:
        # Get the ClassroomPerformance model dynamically
        ClassroomPerformance = apps.get_model('classroom_performances', 'ClassroomPerformance')

        classroom_performance = ClassroomPerformance.objects.get(id=classroom_performance_id)
        classroom_performance.update_performance_metrics()
    except ClassroomPerformance.DoesNotExist:
        # Handle error
        raise Reject('Could not update classroom performance metrics, classroom performance object in your school with the provided credentials does not exist, please check the classroom details and try again.')
    except Exception as e:
        self.retry(exc=e)
    finally:
        system_utilities.release_lock(lock_id)