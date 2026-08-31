from celery import shared_task

from apps.markets.services.status_refresh import refresh_available_markets_to_possible


@shared_task(
    name="apps.markets.tasks.refresh_market_possible_status",
    ignore_result=True,
    acks_late=True,
)
def refresh_market_possible_status():
    return refresh_available_markets_to_possible()
