from django.urls import path

from apps.orders.api.views.crud import (ListCreateOrderAPIView,
                                   OrderDetailView,
                                   OrderStatusUpdateAPIView)
from apps.orders.api.views.todays_orders import (TodaysDeliveringOrdersCountAPIView,
                                                 TodaysDeliveringMarketsListAPIView,
                                                 MyOrdersTotalPriceAPIView,
                                                 TotalPriceByAllUsersOrderAPIView)


urlpatterns = [
    path('',ListCreateOrderAPIView.as_view()),
    path('<uuid:id>/',OrderDetailView.as_view()),
    path('<uuid:id>/status/',OrderStatusUpdateAPIView.as_view()),
    path('today/count-of-orders',TodaysDeliveringOrdersCountAPIView.as_view()),
    path('today/delivering-markets',TodaysDeliveringMarketsListAPIView.as_view()),
    path('my-order-price',MyOrdersTotalPriceAPIView.as_view()),
    path('users-total-price',TotalPriceByAllUsersOrderAPIView.as_view())
]
