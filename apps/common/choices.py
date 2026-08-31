
USER_ROLE_CHOICES = {
    "ADMIN": "Admin",
    "DELIVERER": "Yetkazuvchi",
    "AGENT":"Agent",
    "CUSTOMER":"Mijoz"
}


PRODUCT_UNIT_CHOICES = {
    "KG": "kg",
    "GR": "gr",
    "UNIT": "dona",
}


ORDER_STATUS_CHOICES = {
    "APPROVED": "Tasdiqlangan",
    "REJECTED": "Rad etilgan",
    "PENDING": "Tasdiqlanishi kutilmoqda",
    "CANCELLED": "Bekor qilindi",
    "DELIVERED": "Yetkazildi",
   
}


MARKET_STATUS_CHOICES = {
    "WAITING": "Buyurtmani kutmoqda",
    "AVAILABLE": "Mahsulotlar mavjud",
    "POSSIBLE": "Mahsulot kerak bo'lishi mumkin",
    "NOT_NEEDED": "Hozircha buyurtma kerak emas",
    "PENDING":"Buyurtma tasdiqlanishi kutilmoqda"
}


MARKET_COLOR_CHOICES = {
    "PENDING": "#A855F7",     # Purple
    "WAITING": "#3B82F6",     # Blue
    "AVAILABLE": "#22C55E",   # Green
    "POSSIBLE": "#F59E0B",    # Amber
    "NOT_NEEDED": "#EF4444",  # Red
}
