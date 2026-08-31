from django.contrib.gis.db import models
from apps.common.models import BaseModel
from apps.common.choices import MARKET_STATUS_CHOICES, MARKET_COLOR_CHOICES


class Market(BaseModel):
    name = models.CharField(max_length=100,db_index=True)
    location = models.PointField(srid=4326,geography=True,null=True,blank=True)
    image = models.ImageField(upload_to='market_images/', blank=True, null=True)
    description = models.TextField(blank=True)
    owner = models.ForeignKey("users.User", on_delete=models.CASCADE, null=True, related_name='markets')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, related_name='created_markets')
    credit_amount = models.DecimalField(max_digits=20,decimal_places=3,default=0)
    def save(self, *args, **kwargs):
        if self.discount_percentage < 0 or self.discount_percentage > 100:
            raise ValueError("Discount percentage must be between 0 and 100.")
        super().save(*args, **kwargs)
    def __str__(self):
        return self.name
    
class MarketStatus(BaseModel):
    market = models.OneToOneField(Market, on_delete=models.CASCADE, related_name='statuses')
    status = models.CharField(max_length=50, choices=MARKET_STATUS_CHOICES, default="NOT_NEEDED")
    color_code = models.CharField(max_length=20,choices = MARKET_COLOR_CHOICES,default = "WAITING")
    updated_at = models.DateTimeField(auto_now=True)

    last_order = models.ForeignKey("orders.Order",null=True,blank=True,on_delete=models.SET_NULL,related_name="market_status")
    def __str__(self):
        return f"MarketStatus {self.id} for Market {self.market.name}"
    
