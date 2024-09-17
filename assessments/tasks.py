# celery
from celery import shared_task


@shared_task
def add(x, y):
    result = x + y
    print(f'Task executed: {x} + {y} = {result}')
    return result