# celery
from celery import shared_task
from celery.exceptions import Reject

# models
from .models import Assessment

# utility functions
from seeran_backend import utils as system_utilities

# tasks
from classrooms.tasks import update_classroom_performance_metrics_task


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def update_assessment_performance_metrics_task(self, assessment_id):
    lock_id = f'update_assessment_performance_metrics_task_{assessment_id}'
    if not system_utilities.acquire_lock(lock_id):
        raise Reject('Task is already queued or running')

    try:
        assessment = Assessment.objects.get(id=assessment_id)
        assessment.update_performance_metrics()
        update_classroom_performance_metrics_task.delay(assessment.classroom_id)
    except Assessment.DoesNotExist:
        # Handle error
        raise Reject('an assessment in your school with the provided credentials does not exist, please check the assessment details and try again')
    except Exception as e:
        self.retry(exc=e)
    finally:
        system_utilities.release_lock(lock_id)

