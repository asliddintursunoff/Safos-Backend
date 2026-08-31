
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django_filters import rest_framework as filters

from apps.markets.models import Market, MarketStatus
from apps.common.choices import MARKET_STATUS_CHOICES

class MarketFilter(filters.FilterSet):
    status = filters.ChoiceFilter(field_name="statuses__status",choices=tuple(MARKET_STATUS_CHOICES.items()))
    longitude = filters.NumberFilter(method="filter_distance")
    latitude = filters.NumberFilter(method="filter_distance")
    radius_in_meters = filters.NumberFilter(method='filter_distance')
    class Meta:
        model = Market
        fields = ['status','latitude','longitude']

    def filter_distance(self, queryset, name, value):
        longitude = self.data.get("longitude")
        latitude = self.data.get("latitude")
        radius = self.data.get("radius_in_meters", 200)

        if longitude and latitude:
            longitude = float(longitude)
            latitude = float(latitude)
            radius = float(radius)

            user_location = Point(longitude, latitude, srid=4326)

            queryset = queryset.filter(
                location__dwithin=(user_location, D(m=radius))
            )

        return queryset