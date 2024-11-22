from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import connection
import re
from .models import Transaction
from dateutil import parser
from datetime import datetime, timedelta
from django.db.models import Q
from django.http import JsonResponse
 
class TransactionView(APIView):
    def get(self, request):
        query_string = request.GET.get('query', '')
        if not query_string:
            return Response({"error": "Query string is required"}, status=400)
        elif query_string.strip().lower() == "hi":
            return Response(
                {
                    "type": "text",
                    "owner": "bot",
                    "timestamp": str(datetime.now()),
                    "content": "Hello! I am a chatbot."
                }
            )
 
        query_string = query_string.lower()
        conditions = Q()
 
        # Helper function to parse date strings
        def parse_dates(query_string):
            date_patterns = [
                r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b",  # dd-mm-yyyy or dd/mm/yyyy
                r"\b(\d{1,2})[-/](\w{3,9})[-/](\d{4})\b",  # dd-mmm-yyyy or dd/mmm/yyyy
                r"\b(\w{3,9})\s(\d{1,2}),\s(\d{4})\b",  # month dd, yyyy
                r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b"  # yyyy-mm-dd or yyyy/mm/dd
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
            return dates
 
        # Helper function to parse amount-based conditions
        def parse_amount_conditions(query_string):
            amount_conditions = Q()
            match = re.search(r'greater than (\d+)', query_string)
            if match:
                amount_conditions &= Q(amount__gt=int(match.group(1)))
 
            match = re.search(r'less than (\d+)', query_string)
            if match:
                amount_conditions &= Q(amount__lt=int(match.group(1)))
 
            match = re.search(r'above (\d+)', query_string)
            if match:
                amount_conditions &= Q(amount__gt=int(match.group(1)))
 
            match = re.search(r'below (\d+)', query_string)
            if match:
                amount_conditions &= Q(amount__lt=int(match.group(1)))
 
            match = re.search(r'between (\d+) and (\d+)', query_string)
            if match:
                lower = int(match.group(1))
                upper = int(match.group(2))
                amount_conditions &= Q(amount__gte=lower, amount__lte=upper)
 
            match = re.search(r'exactly (\d+)', query_string)
            if match:
                amount_conditions &= Q(amount=int(match.group(1)))
 
            return amount_conditions
 
        # Parse dates from the query string
        dates = parse_dates(query_string)
        dates.sort()
 
        # Date-based condition handlers
        condition_handlers = {
            'range': lambda dates: Q(date__gte=dates[0]) & Q(date__lte=dates[1]),
            'after': lambda date: Q(date__gt=date),
            'before': lambda date: Q(date__lt=date),
            'today': lambda _: Q(date=datetime.now().date()),
            'yesterday': lambda _: Q(date=(datetime.now() - timedelta(days=1)).date()),
            'last_n_days': lambda n: Q(date__gte=datetime.now().date() - timedelta(days=n))
        }
 
        # Non-date-specific handlers
        non_date_condition_handlers = {
            'till_today': lambda: Q(date__lte=datetime.now().date()),
            'till_yesterday': lambda: Q(date__lte=(datetime.now() - timedelta(days=1)).date()),
            'till_day_before_yesterday': lambda: Q(date__lte=(datetime.now() - timedelta(days=2)).date()),
            'day_before_yesterday': lambda: Q(date=(datetime.now() - timedelta(days=2)).date()),
        }
 
        # Handle date conditions
        if len(dates) == 2:
            conditions &= condition_handlers['range'](dates)
        elif len(dates) == 1:
            only_date = dates[0]
            if "after" in query_string:
                conditions &= condition_handlers['after'](only_date)
            elif "before" in query_string:
                conditions &= condition_handlers['before'](only_date)
            elif "till yesterday" in query_string or "till today" in query_string:
                end_date = datetime.now().date() - timedelta(days=1) if "till yesterday" in query_string else datetime.now().date()
                conditions &= Q(date__gte=only_date) & Q(date__lte=end_date)
            else:
                conditions &= Q(date=only_date)
        if not dates:
            if "till today" in query_string or "till now" in query_string:
                today = datetime.now().date()
                conditions &= Q(date__lte=today)
            elif "till yesterday" in query_string:
                yesterday = (datetime.now() - timedelta(days=1)).date()
                conditions &= Q(date__lte=yesterday)
            elif "till day before yesterday" in query_string:
                day_before_yesterday = (datetime.now() - timedelta(days=2)).date()
                conditions &= Q(date__lte=day_before_yesterday)
            elif "day before yesterday" in query_string:
                day_before_yesterday = (datetime.now() - timedelta(days=2)).date()
                conditions &= Q(date=day_before_yesterday)
            elif "yesterday" in query_string:
                yesterday = (datetime.now() - timedelta(days=1)).date()
                conditions &= Q(date=yesterday)
            elif "today" in query_string:
                today = datetime.now().date()
                conditions &= Q(date=today)


        if "last" in query_string and "days" in query_string:
            match = re.search(r'last (\d+) days', query_string)
            if match:
                days = int(match.group(1))
                # Check for specific conditions in the query to adjust the date range
                if "till yesterday" in query_string:
                    # n days till yesterday: Exclude today, use n days up to yesterday
                    end_date = datetime.now().date() - timedelta(days=1)
                    start_date = end_date - timedelta(days=days)
                    conditions &= Q(date__gte=start_date) & Q(date__lte=end_date)
                elif "till day before yesterday" in query_string:
                    # n days till the day before yesterday: Exclude today and yesterday
                    end_date = datetime.now().date() - timedelta(days=2)
                    start_date = end_date - timedelta(days=days)
                    conditions &= Q(date__gte=start_date) & Q(date__lte=end_date)
                else:
                    # Default: n days from today
                    start_date = datetime.now().date() - timedelta(days=days)
                    conditions &= Q(date__gte=start_date) & Q(date__lte=datetime.now().date())
 
        # Handle non-date-specific conditions
        for key, handler in non_date_condition_handlers.items():
            if key.replace("_", " ") in query_string:
                conditions &= handler()
 
        # Handle amount conditions
        conditions &= parse_amount_conditions(query_string)
 
        # Status-based conditions
        status_conditions = Q()
        if any(word in query_string for word in ["successful", "completed", "done", "paid", "approved"]):
            status_conditions |= Q(status="Successful")
        if any(word in query_string for word in ["failed", "declined", "rejected", "error", "cancelled", "bounced"]):
            status_conditions |= Q(status="Failed")
        if any(word in query_string for word in ["pending", "processing", "on hold", "awaiting", "in progress"]):
            status_conditions |= Q(status="Processing")
 
        if status_conditions.children:
            conditions &= status_conditions
 
        # Transaction type-based conditions
        if any(word in query_string for word in ["credited", "deposit", "added", "received"]):
            conditions &= Q(transaction_type="Credited")
        if any(word in query_string for word in ["debited", "withdrawn", "spent", "deducted"]):
            conditions &= Q(transaction_type="Debited")
 
        try:
            transactions = Transaction.objects.filter(conditions)
            print(str(transactions.query))
            results = list(transactions.values())
            if results:
                return Response(
                {
                    "type": "grid",
                    "owner": "bot",
                    "timestamp": str(datetime.now()),
                    "content": {
                        "columns": [
                            {"column_name": "serial_no", "column_type": "integer"},
                            {"column_name": "date", "column_type": "date"},
                            {"column_name": "transaction_id", "column_type": "string"},
                            {"column_name": "amount", "column_type": "float"},
                            {"column_name": "transaction_type", "column_type": "string"},
                            {"column_name": "status", "column_type": "string"}
                        ],
                        "data": results
                    }
                }
            )
            else:
                return Response(
                    {
                        "type": "text",
                        "owner": "bot",
                        "timestamp": str(datetime.now()),
                        "content": "No transactions found matching your query."
                    }
                )
        except Exception as e:
            return Response({"error": str(e)}, status=500)
