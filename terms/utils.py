# python 
from datetime import date

# models
from terms.models import Term


def get_current_term(school, grade):
    today = date.today()
    term = Term.objects.filter(
        school=school,
        grade=grade,
        start_date__lte=today,  # Term started before or on today
        end_date__gte=today      # Term ends after or on today
    ).first()

    return term if term else None

def get_previous_term(school, grade, end_date=None):
    today = end_date if end_date else date.today()
    
    # Filter for terms that ended before today and order by end_date descending
    previous_term = Term.objects.filter(
        school=school,
        grade=grade,
        end_date__lt=today  # Term ended before today
    ).order_by('-end_date').first()  # Get the most recent term before today

    return previous_term if previous_term else None