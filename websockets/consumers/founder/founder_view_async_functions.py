# channels
from channels.db import database_sync_to_async

# django

# models 
from schools.models import School

# serializers
from schools.serializers import SchoolsSerializer


@database_sync_to_async
def view_schools():
    """
    Asynchronously fetches all School records from the database and serializes them.

    This function retrieves all the schools from the School model and serializes the data
    using the SchoolsSerializer. It handles potential exceptions by returning a general error message.

    Returns:
        dict: A dictionary containing either the serialized schools or an error message.
            - If successful, returns {'schools': serialized_schools} where serialized_schools is a list of serialized school data.
            - If an exception occurs, returns {'error': str(e)} with the exception message.
    """
    try:
        # Fetch all School records from the database
        schools = School.objects.all()
        
        # Serialize the fetched schools data
        serialized_schools = SchoolsSerializer(schools, many=True).data

        # Return the serialized data in a dictionary
        return {'schools': serialized_schools}

    except Exception as e:
        # Handle any unexpected errors and return a general error message
        return {'error': str(e).lower()}

