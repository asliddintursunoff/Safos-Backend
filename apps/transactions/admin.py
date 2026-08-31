from django.contrib import admin
from .models import PaymentAllocation,Payment

admin.site.register(Payment)
admin.site.register(PaymentAllocation)