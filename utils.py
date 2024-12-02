from datetime import datetime

def get_next_occurrence(day, reference_date=None):
    if reference_date is None:
        reference_date = datetime.now()
    
    try:
        next_date = datetime(reference_date.year, reference_date.month, day)
        if next_date < reference_date:
            if reference_date.month == 12:
                next_date = datetime(reference_date.year + 1, 1, day)
            else:
                next_date = datetime(reference_date.year, reference_date.month + 1, day)
    except ValueError:
        # Handle invalid dates (e.g., February 30)
        if reference_date.month == 12:
            next_date = datetime(reference_date.year + 1, 1, day)
        else:
            next_date = datetime(reference_date.year, reference_date.month + 1, day)
    
    return next_date