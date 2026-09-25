"""
Receipt printing.

The bot used to put the whole receipt into the "🖨 Print" button url. For long orders
that url is bigger than Telegram allows ("Reply markup is too long"). Now the bot can
use a short signed link to this service instead, and we redirect to exactly the same
print page with exactly the same data, so the printed result does not change.
"""
import hashlib
import hmac
import urllib.parse
from datetime import datetime
from typing import Optional

from app.core.config import settings

PRINT_PAGE_URL = "https://asliddintursunoff.github.io/url-redirect/print.html"


def _secret() -> bytes:
    raw = settings.PRINT_SECRET or ("print:" + settings.DATABASE_URL)
    return hashlib.sha256(raw.encode()).digest()


def sign_order_id(order_id: int) -> str:
    return hmac.new(_secret(), f"order:{order_id}".encode(), hashlib.sha256).hexdigest()[:24]


def verify_order_signature(order_id: int, token: str) -> bool:
    return hmac.compare_digest(sign_order_id(order_id), token or "")


def public_base_url() -> Optional[str]:
    if settings.PUBLIC_URL:
        return settings.PUBLIC_URL.rstrip("/")
    if settings.RAILWAY_PUBLIC_DOMAIN:
        return f"https://{settings.RAILWAY_PUBLIC_DOMAIN}"
    return None


def signed_print_url(order_id: int) -> Optional[str]:
    base = public_base_url()
    if not base or order_id is None:
        return None
    return f"{base}/print/orders/{order_id}?t={sign_order_id(order_id)}"


def _fmt_dt(value) -> str:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.strftime("%d-%m-%Y %H:%M")


def build_receipt_text(order) -> str:
    """Same layout as formatter/printer_check.py in the bot."""
    ESC = "\x1B"
    GS = "\x1D"

    bold_on = ESC + "E" + "\x01"
    bold_off = ESC + "E" + "\x00"
    center = ESC + "a" + "\x01"
    left = ESC + "a" + "\x00"
    big_on = GS + "!" + "\x33"
    big_off = GS + "!" + "\x00"

    line_width = 48
    sep_line = "█" * line_width

    name_w = 16
    price_w = 10
    qty_w = 12
    sum_w = 10

    lines = []

    lines.append(center + bold_on + big_on + "SAFOS\n" + big_off + bold_off)
    lines.append(center + "Sof mahsulot\n")
    lines.append(sep_line + "\n")

    agent = order.agent
    if agent:
        agent_name = f"{agent.first_name or ''} {agent.last_name or ''}".strip()
        lines.append(left + bold_on + "Agent: " + bold_off + f"{agent_name}\n")

    dostavchik = order.dostavchik
    if dostavchik:
        d_name = f"{dostavchik.first_name or ''} {dostavchik.last_name or ''}".strip()
        lines.append(bold_on + "Dostavchik: " + bold_off + f"{d_name}\n")

    lines.append("\n")

    for_who = order.for_who if order.for_who is not None else "Noma’lum"
    lines.append(bold_on + "Buyurtma egasi: " + bold_off + f"{for_who}\n")

    if order.order_date:
        lines.append(bold_on + "Olingan vaqt: " + bold_off + f"{_fmt_dt(order.order_date)}\n")

    if order.delivered_date:
        lines.append(bold_on + "Yetkazilgan: " + bold_off + f"{_fmt_dt(order.delivered_date)}\n")

    lines.append(sep_line + "\n")

    lines.append(
        bold_on +
        f"{'Nomi':<{name_w}}{'Narx':<{price_w}}{'Soni':<{qty_w}}{'Summa':>{sum_w}}\n" +
        bold_off
    )
    lines.append(sep_line + "\n")

    total = 0
    for item in order.items:
        if not item.product:
            continue
        product_name = (item.product.name or "")[:name_w]
        price = int(item.product.price or 0)
        qty = int(item.quantity or 0)
        unit = item.product.unit
        unit = getattr(unit, "value", unit)
        line_total = qty * price
        total += line_total

        price_str = f"{price:,}"
        qty_str = f"{qty:,} {unit}"
        total_str = f"{line_total:,}"

        lines.append(
            f"{product_name:<{name_w}}{price_str:<{price_w}}{qty_str:<{qty_w}}{total_str:>{sum_w}}\n"
        )
        lines.append(sep_line + "\n")

    total_str = f"{total:,}"
    lines.append(bold_on + f"{'Jami:':<{name_w+price_w+qty_w}}{total_str:>{sum_w}}\n" + bold_off)

    lines.append("\n")
    lines.append("\n")
    sign_line = "IMZO:  "
    lines.append(sign_line + "\n")
    lines.append("       " + "█" * (line_width - len(sign_line)))

    lines.append(center + bold_on + "Rahmat! Yana kutib qolamiz!\n" + bold_off)
    lines.append(center + "\n\n\n")

    return "".join(lines)


def build_print_page_url(order) -> str:
    return f"{PRINT_PAGE_URL}?data={urllib.parse.quote(build_receipt_text(order))}"
