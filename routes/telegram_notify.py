import requests
from flask import current_app

REQUEST_TIMEOUT = 5


def notify_new_order(order):
    """Надсилає в Telegram повідомлення про нове замовлення.
    Помилки Telegram/мережі не повинні ламати оформлення замовлення —
    тому все загортаємо в try/except і просто логуємо збій."""
    token = current_app.config.get("TELEGRAM_BOT_TOKEN")
    chat_id = current_app.config.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        current_app.logger.info("Telegram-сповіщення пропущено — не задано TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID")
        return

    lines = [
        f"🛒 Нове замовлення №{order.id}",
        "",
        f"👤 {order.customer_name}",
        f"📞 {order.phone}",
    ]
    if order.email:
        lines.append(f"✉️ {order.email}")
    lines.append(f"📍 {order.city}, {order.np_branch}")
    if order.comment:
        lines.append(f"💬 {order.comment}")

    lines.append("")
    for item in order.items:
        line_total = float(item.price) * item.quantity
        variant = f"{item.size.color.name}, {item.size.size}" if item.size.color else item.size.size
        lines.append(f"• {item.product.name} ({variant}) × {item.quantity} — {line_total:.0f} ₴")

    lines.append("")
    lines.append(f"Разом: {order.total:.0f} ₴")

    text = "\n".join(lines)
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        requests.post(
            url,
            json={"chat_id": chat_id, "text": text},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        current_app.logger.warning("Не вдалося надіслати сповіщення про замовлення в Telegram", exc_info=True)