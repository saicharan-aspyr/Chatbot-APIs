from django.db import models

class Transaction(models.Model):
    # Auto-incrementing primary key for s.no
    serial_no = models.AutoField(primary_key=True)
    
    # Date of the transaction
    date = models.DateField(null=False)
    
    # Unique ID for the transaction
    transaction_id = models.CharField(max_length=100, unique=True,null=False)
    
    #amount
    amount = models.DecimalField(max_digits=20, decimal_places=2)

    
    # Indicates whether the transaction is credited or debited
    transaction_type = models.CharField(
        max_length=10,
        choices=[('Credited', 'Credited'), ('Debited', 'Debited')]
    )
    
    # Status of the transaction
    status = models.CharField(
        max_length=20,
        choices=[
            ('Processing', 'Processing'),
            ('Failed', 'Failed'),
            ('Successful', 'Successful')
        ]
    )

    def __str__(self):
        return f"{self.transaction_id} - {self.status}"
