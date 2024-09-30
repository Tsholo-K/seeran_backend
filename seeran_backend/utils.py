# python
import gzip
from io import BytesIO

# celery
from celery.signals import task_failure

# django
from django.core.cache import cache


def compress_data(data):
    buf = BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb') as f:
        f.write(data.encode('utf-8'))
    return buf.getvalue()

LOCK_EXPIRE = 60 * 15  # Lock expires after 15 minutes

def acquire_lock(lock_id):
    # Try to set a lock in the cache
    return cache.add(lock_id, 'locked', LOCK_EXPIRE)

def release_lock(lock_id):
    cache.delete(lock_id)

@task_failure.connect
def task_failed_handler(sender=None, **kwargs):
    task_id = kwargs['task_id']
    exception = kwargs['exception']
    # Log the failure or take other actions
    print(f'Task {task_id} failed with exception: {exception}')
