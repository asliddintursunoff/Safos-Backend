from django.urls import path

from .views.debt_pay import TakePaymentFromMarketCreateAPIView, WorkerStatisticsAPIView

urlpatterns = [
    path('', TakePaymentFromMarketCreateAPIView.as_view()),
    path('worker-statistics/', WorkerStatisticsAPIView.as_view()),
]
