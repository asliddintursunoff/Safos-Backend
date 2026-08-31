from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from apps.common.permissions import IsAdminOrReadOnly
from apps.products.models import Product, ProductCategory
from .serializers import ProductSerializer, ProductCategoryReadSerializer, ProductCategorySerializer

class ProductsCreateListView(ListCreateAPIView):
    queryset = ProductCategory.objects.prefetch_related('products').all()
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    permission_classes = [IsAdminOrReadOnly]
    def get_queryset(self):
        if self.request.method == 'GET':
            return ProductCategory.objects.prefetch_related('products').all()
        else :
            return Product.objects.all()
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ProductCategoryReadSerializer
        return ProductSerializer
    
class ProductDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'id'
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    permission_classes = [IsAdminOrReadOnly]
    
class ProductCategoryListView(ListCreateAPIView):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    permission_classes = [IsAdminOrReadOnly]



class ProductCategoryDetailView(RetrieveUpdateDestroyAPIView):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    lookup_field = 'id'
    permission_classes = [IsAdminOrReadOnly]
    
    
