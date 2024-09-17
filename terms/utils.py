# python 
from datetime import date

# models
from terms.models import Term


def get_current_term(school, grade):
    today = date.today()
    term = Term.objects.filter(school=school, grade=grade, start_date__lte=today, end_date__gte=today).first()

    return term if term else None
