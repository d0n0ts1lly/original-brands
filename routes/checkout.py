from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from models import Order, OrderItem, Product, ProductSize, db
from .telegram_notify import notify_new_order

checkout_bp = Blueprint("checkout", __name__)


def _get_cart():
    return session.setdefault("cart", {})


def _cart_items():
    cart = _get_cart()
    items = []
    total = 0
    stale = False

    for key, qty in list(cart.items()):
        product_id, size_id = key.split(":")
        product = Product.query.get(int(product_id))
        size = ProductSize.query.get(int(size_id))
        if not product or not size:
            del cart[key]
            stale = True
            continue
        subtotal = float(product.display_price) * qty
        total += subtotal
        items.append({"key": key, "product": product, "size": size, "quantity": qty, "subtotal": subtotal})

    if stale:
        session.modified = True

    return items, total


@checkout_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    items, total = _cart_items()
    if not items:
        flash("Кошик порожній — спершу додайте товари", "error")
        return redirect(url_for("catalog.catalog"))

    if request.method == "POST":
        form = request.form
        customer_name = form.get("customer_name", "").strip()
        phone = form.get("phone", "").strip()
        email = form.get("email", "").strip()
        city = form.get("city", "").strip()
        np_branch = form.get("np_branch", "").strip()
        comment = form.get("comment", "").strip()

        errors = []
        if not customer_name:
            errors.append("Вкажіть ПІБ отримувача")
        if not phone:
            errors.append("Вкажіть номер телефону")
        if not city:
            errors.append("Вкажіть місто")
        if not np_branch:
            errors.append("Вкажіть відділення або поштомат Нової пошти")

        # звіряємо залишки ще раз прямо перед створенням замовлення —
        # товар міг закінчитись, поки лежав у кошику
        for item in items:
            fresh_size = ProductSize.query.get(item["size"].id)
            available = fresh_size.quantity if fresh_size else 0
            if available < item["quantity"]:
                errors.append(
                    f"«{item['product'].name}» ({item['size'].size}): у наявності лише {available} шт."
                )

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("checkout.html", items=items, total=total, form=form), 400

        order = Order(
            customer_name=customer_name, phone=phone, email=email or None,
            city=city, np_branch=np_branch, comment=comment or None,
        )
        db.session.add(order)
        db.session.flush()

        for item in items:
            fresh_size = ProductSize.query.get(item["size"].id)
            fresh_size.quantity -= item["quantity"]
            db.session.add(OrderItem(
                order_id=order.id, product_id=item["product"].id, size_id=item["size"].id,
                price=item["product"].display_price, quantity=item["quantity"],
            ))

        db.session.commit()

        notify_new_order(order)

        session["cart"] = {}
        session["last_order_id"] = order.id
        session.modified = True
        return redirect(url_for("checkout.confirmation", order_id=order.id))

    return render_template("checkout.html", items=items, total=total, form={})


@checkout_bp.route("/order/<int:order_id>/confirmation")
def confirmation(order_id):
    # показуємо підтвердження лише тому, хто щойно оформив саме це замовлення
    if session.get("last_order_id") != order_id:
        abort(404)
    order = Order.query.get_or_404(order_id)
    return render_template("order_confirmation.html", order=order)