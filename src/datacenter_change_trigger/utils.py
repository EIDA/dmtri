from datetime import datetime

KNOWN_DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
]

def parse_date_string(date_str: str, end: bool = False) -> str:
    for fmt in KNOWN_DATE_FORMATS:
        try:
            dt = datetime.strptime(date_str, fmt)
            if end and dt.hour == 0 and dt.minute == 0 and dt.second == 0:
                dt = dt.replace(hour=23, minute=59, second=59)
            return dt.isoformat()
        except ValueError:
            continue
    raise ValueError(f"Invalid date: '{date_str}'. Accepted formats: YYYY-MM-DD or ISO 8601.")
