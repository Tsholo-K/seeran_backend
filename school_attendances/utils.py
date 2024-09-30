from datetime import datetime

def get_month_dates(month_name, year=datetime.now().year):
    month_names = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
    month = month_names.index(month_name.lower()) + 1
    start_date = datetime(year, month, 1)
    end_date = datetime(year, month+1, 1) if month < 12 else datetime(year+1, 1, 1)
    return start_date, end_date