from flask import flash, redirect, render_template, request, url_for

from models import Order, db
from . import admin_bp

STATUSES = ["new", "processing", "shipped", "completed", "cancelled"]
STATUS_LABELS = {
    "new": "Нове",
    "processing": "В обробці",
    "shipped": "Відправлено",
    "completed": "Виконано",
    "cancelled": "Скасовано",
}


@admin_bp.route("/orders")
def orders_list():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin/orders_list.html", orders=orders, status_labels=STATUS_LABELS)


@admin_bp.route("/orders/<int:order_id>", methods=["GET", "POST"])
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)

    if request.method == "POST":
        status = request.form.get("status", "").strip()
        np_ttn = request.form.get("np_ttn", "").strip()
        customer_name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        city = request.form.get("city", "").strip()
        np_branch = request.form.get("np_branch", "").strip()
        comment = request.form.get("comment", "").strip()

        errors = []
        if status not in STATUSES:
            errors.append("Некоректний статус")
        if not customer_name:
            errors.append("Вкажіть ПІБ отримувача")
        if not phone:
            errors.append("Вкажіть телефон")
        if not city:
            errors.append("Вкажіть місто")
        if not np_branch:
            errors.append("Вкажіть відділення Нової пошти")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "admin/order_detail.html", order=order, statuses=STATUSES, status_labels=STATUS_LABELS
            ), 400

        previous_status = order.status
        order.status = status
        order.np_ttn = np_ttn or None
        order.customer_name = customer_name
        order.phone = phone
        order.email = email or None
        order.city = city
        order.np_branch = np_branch
        order.comment = comment or None

        # При скасуванні замовлення — повертаємо товар на склад.
        # Якщо скасування скасовують назад — знову списуємо (щоб залишки не розходились).
        if status == "cancelled" and previous_status != "cancelled":
            for item in order.items:
                if item.size:
                    item.size.quantity += item.quantity
        elif previous_status == "cancelled" and status != "cancelled":
            for item in order.items:
                if item.size:
                    item.size.quantity -= item.quantity

        db.session.commit()
        flash(f"Замовлення №{order.id} оновлено", "success")
        return redirect(url_for("admin.order_detail", order_id=order.id))

    return render_template(
        "admin/order_detail.html", order=order, statuses=STATUSES, status_labels=STATUS_LABELS
    )