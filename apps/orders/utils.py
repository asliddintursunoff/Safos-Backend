from datetime import datetime
from django.utils import timezone
from rest_framework.exceptions import ValidationError
def parse_date(value: str):
    try:
        return datetime.strptime(value, "%d-%m-%Y").date()
    except (ValueError, TypeError):
        raise ValidationError(
            {"date": "Invalid date format. Use dd-mm-yyyy (example: 25-08-2026)"}
        )


def get_date_filters(request):
    """
    Supports:
      ?date=25-08-2026
      ?start_date=01-08-2026&end_date=25-08-2026
    """
    date_str = request.query_params.get("date")
    start_str = request.query_params.get("start_date")
    end_str = request.query_params.get("end_date")

    if date_str:
        d = parse_date(date_str)
        return {"order__created_at__date": d}

    if start_str and end_str:
        start = parse_date(start_str)
        end = parse_date(end_str)
        if start > end:
            raise ValidationError("start_date must be earlier than or equal to end_date")
        return {
            "order__created_at__date__gte": start,
            "order__created_at__date__lte": end,
        }

    today = timezone.localdate()
    return {"order__created_at__date": today}