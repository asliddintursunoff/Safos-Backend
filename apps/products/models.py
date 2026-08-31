from django.contrib.gis.db import models

from apps.common.models import BaseModel
from apps.common.choices import PRODUCT_UNIT_CHOICES


class ProductCategory(BaseModel):
    name = models.CharField(max_length=100,db_index=True)
    def __str__(self):
        return self.name
    
class Product(BaseModel):
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=100,db_index=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=15, decimal_places=3)
    unit = models.CharField(max_length=10, choices=PRODUCT_UNIT_CHOICES, default="UNIT")
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    picture = models.ImageField(upload_to='product_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id}  {self.name}"