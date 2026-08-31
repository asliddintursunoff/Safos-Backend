from django.urls import path
from .views import ProductsCreateListView,ProductCategoryListView, ProductCategoryDetailView, ProductDetailView

urlpatterns = [
    path('', ProductsCreateListView.as_view(), name='product-category-list'),
    path('<uuid:id>/', ProductDetailView.as_view(), name='product-detail'),
    path('categories/', ProductCategoryListView.as_view(), name='product-category-detail'),
    path('categories/<uuid:id>/', ProductCategoryDetailView.as_view(), name='product-category-detail'),
]