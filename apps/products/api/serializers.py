from rest_framework import serializers
from apps.products.models import Product,ProductCategory




class ProductSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=ProductCategory.objects.all())
    unit_display = serializers.CharField(source="get_unit_display", read_only=True)
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price','unit','unit_display','value','picture', 'category']


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ['id', 'name']
        
class ProductCategoryReadSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)
    class Meta:
        model = ProductCategory
        fields = ['id', 'name','products']
        


