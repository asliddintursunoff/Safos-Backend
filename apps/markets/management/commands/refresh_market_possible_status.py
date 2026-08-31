from django.core.management.base import BaseCommand

from apps.markets.services.status_refresh import refresh_available_markets_to_possible


class Command(BaseCommand):
    help = (
        "Set AVAILABLE markets to POSSIBLE after their delivered-order cadence "
        "(default 5 days, or the gap learned from the last 3 delivered orders)."
    )

    def handle(self, *args, **options):
        result = refresh_available_markets_to_possible()
        self.stdout.write(
            self.style.SUCCESS(
                "checked={checked} updated={updated} skipped={skipped}".format(
                    **result
                )
            )
        )
