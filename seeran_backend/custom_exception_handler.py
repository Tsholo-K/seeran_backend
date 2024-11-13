from rest_framework.views import exception_handler
from rest_framework import status

def custom_exception_handler(exc, context):
    # Call the default exception handler first
    response = exception_handler(exc, context)

    # Check if the exception is a throttling error (status code 429)
    if response is not None and response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        # Modify the response to include custom error message
        response.data = {'error': 'Could not process your request, too many requests received from your IP address. Please try again later.',}

    return response
