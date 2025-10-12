from fastapi import HTTPException

def calculate_total_items(orders: list):
    """
    Calculate total quantity for each product across all orders,
    returning a string with the unit.
    :param orders: List of Order objects from the DB
    :return: dict like {"Apple": "10 kg", "Banana": "5 dona", ...}
    """
    if not orders:
        raise HTTPException(status_code=404, detail="Zakas mavjud emas!")

    total_items = {}

    for order in orders:
        if not order.items:
            continue

        for item in order.items:
            if not item or not item.product:
                continue

            product_name = item.product.name
            quantity = item.quantity or 0
            unit = item.product.unit or "dona"

            if product_name in total_items:
                prev_qty_str = total_items[product_name].split()[0]
                prev_qty = float(prev_qty_str)  # ✅ Keep as float
                total_items[product_name] = f"{prev_qty + quantity} {unit}"
            else:
                total_items[product_name] = f"{quantity} {unit}"

    return total_items
