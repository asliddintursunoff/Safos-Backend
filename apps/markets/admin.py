from django.contrib import admin

from .models import Market, MarketStatus


class MarketStatusInline(admin.StackedInline):
    model = MarketStatus
    extra = 0
    can_delete = False


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    inlines = [MarketStatusInline]


@admin.register(MarketStatus)
class MarketStatusAdmin(admin.ModelAdmin):
    pass