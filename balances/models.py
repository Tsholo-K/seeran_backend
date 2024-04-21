from django.db import models

# models 
from users.models import CustomUser

class Balance(models.Model):
    
    user = models.OneToOneField( CustomUser, on_delete=models.CASCADE, limit_choices_to={'role__in': ['PRINCIPAL', 'STUDENT']}, related_name='balance' )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.email if self.user.email else self.user.id_number} owes {self.amount}'
