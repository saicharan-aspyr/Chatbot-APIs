import re
from dateutil import parser
from datetime import datetime, timedelta
from django.db.models import Q
from decimal import Decimal

def parse_dates(query_string):
    """
    Extracts and parses dates from the query string into a list of YYYY-MM-DD formatted strings.
    """
    date_patterns = [
        r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b",  # dd-mm-yyyy or dd/mm/yyyy
        r"\b(\d{1,2})[-/](\w{3,9})[-/](\d{4})\b",  # dd-mmm-yyyy or dd/mmm/yyyy
        r"\b(\w{3,9})\s(\d{1,2}),\s(\d{4})\b",  # month dd, yyyy
        r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b",  # yyyy-mm-dd or yyyy/mm/dd
    ]
    dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, query_string)
        for match in matches:
            try:
                if re.match(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b", "-".join(match)):
                    parsed_date = datetime.strptime("-".join(match), "%d-%m-%Y")
                else:
                    date_str = "-".join(match)
                    parsed_date = parser.parse(date_str)
                dates.append(parsed_date.strftime("%Y-%m-%d"))
            except ValueError:
                continue
    return sorted(dates)


def parse_date_conditions(query_string, dates):
    """
    Builds date-related filters based on parsed dates and keywords.
    """
    conditions = Q()
    today = datetime.now().date()

    # Handle specific dates
    if len(dates) == 2:
        conditions &= Q(date__gte=dates[0]) & Q(date__lte=dates[1])
    elif len(dates) == 1:
        only_date = dates[0]
        if "after" in query_string or "from" in query_string:
            conditions &= Q(date__gt=only_date)
        elif "before" in query_string:
            conditions &= Q(date__lt=only_date)
        else:
            conditions &= Q(date=only_date)

    # Handle keywords related to dates
    if not dates:  # Handle "no date" cases
        if "till today" in query_string or "till now" in query_string:
            conditions &= Q(date__lte=today)
        elif "till yesterday" in query_string:
            yesterday = today - timedelta(days=1)
            conditions &= Q(date__lte=yesterday)
        elif "till day before yesterday" in query_string:
            day_before_yesterday = today - timedelta(days=2)
            conditions &= Q(date__lte=day_before_yesterday)
        elif "day before yesterday" in query_string:
            day_before_yesterday = today - timedelta(days=2)
            conditions &= Q(date=day_before_yesterday)
        elif "yesterday" in query_string:
            yesterday = today - timedelta(days=1)
            conditions &= Q(date=yesterday)
        elif "today" in query_string:
            conditions &= Q(date=today)
    if "last" in query_string and "days" in query_string:
        match = re.search(r"last (\d+) days", query_string)
        if match:
            days = int(match.group(1))
            start_date = today - timedelta(days=days)
            conditions &= Q(date__gte=start_date) & Q(date__lte=today)

    return conditions


def parse_amount_conditions(query_string):
    """
    Extracts amount-related filters from the query string and builds a Q object.
    """
    amount_conditions = Q()
    amount_mappings = {
    r"(greater than|above) ([\d.]+)": lambda m: Q(amount__gt=Decimal(m.group(2))),
    r"(less than|below) ([\d.]+)": lambda m: Q(amount__lt=Decimal(m.group(2))),
    r"between ([\d.]+) and ([\d.]+)": lambda m: Q(amount__gte=Decimal(m.group(1)), amount__lte=Decimal(m.group(2))),
    r"(exactly) ([\d.]+)": lambda m: Q(amount=Decimal(m.group(2)))  # Added this pattern
   
}
    for pattern, condition in amount_mappings.items():
        match = re.search(pattern, query_string)
        if match:
            amount_conditions &= condition(match)

    return amount_conditions


def parse_status_conditions(query_string):
    """
    Extracts status-related filters from the query string using a dictionary for mapping keywords to statuses.
    """
    status_map = {
        "Successful": ["successful", "completed", "done", "processed", "approved"],
        "Failed": ["failed", "declined", "rejected", "unsuccessful", "cancelled", "bounced"],
        "Processing": ["pending", "processing", "on hold", "awaiting", "in progress"],
    }

    status_conditions = Q()

    for status, keywords in status_map.items():
        if any(word in query_string for word in keywords):
            status_conditions |= Q(status=status)

    return status_conditions



def parse_transaction_type(query_string):
    """
    Extracts transaction type filters from the query string.
    """
    if any(word in query_string for word in ["credited", "deposit", "added", "received"]):
        return Q(transaction_type="Credited")
    if any(word in query_string for word in ["debited", "withdrawn", "spent", "deducted"]):
        return Q(transaction_type="Debited")
    return Q()


def build_query_conditions(query_string):
    """
    Combines all conditions into a final Q object.
    """
    # Extract date-related filters
    dates = parse_dates(query_string)
    date_conditions = parse_date_conditions(query_string, dates)
    
    # Extract amount-related filters
    amount_conditions = parse_amount_conditions(query_string)

    # Extract status-related filters
    status_conditions = parse_status_conditions(query_string)

    # Extract transaction type-related filters
    transaction_type_conditions = parse_transaction_type(query_string)

    # Combine all conditions into a single Q object
    final_conditions = date_conditions & amount_conditions & status_conditions & transaction_type_conditions
    return final_conditions
