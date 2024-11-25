from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import datetime
from django.db.models import Q
from .models import Transaction
from .utils import (
    build_query_conditions
)


class TransactionView(APIView):
    def post(self, request):
        # Retrieve query string from request body
        query_string = request.data.get("query", "").lower()
        if not query_string:
            return Response({"error": "Query string is required"}, status=400)

        if query_string.strip() == "hi":
            return Response(
                {
                    "type": "text",
                    "owner": "bot",
                    "timestamp": str(datetime.now()),
                    "content": "Hello! I am a chatbot.",
                }
            )

        # Initialize conditions
        conditions = Q()
        conditions=build_query_conditions(query_string)

        try:
            # Fetch transactions
            transactions = Transaction.objects.filter(conditions)
            print(conditions)
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
                                {"column_name": "status", "column_type": "string"},
                            ],
                            "data": results,
                        },
                    }
                )
            else:
                return Response(
                    {
                        "type": "text",
                        "owner": "bot",
                        "timestamp": str(datetime.now()),
                        "content": "No transactions found matching your query.",
                    }
                )
        except Exception as e:
            return Response({"error": str(e)}, status=500)
