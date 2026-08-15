from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from models import Product, ProductSize

product_bp = Blueprint("product", __name__)


def _get_cart():
    return session.setdefault("cart", {})


@product_bp.route("/product/<int:product_id>")
def detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("product_detail.html", p=product)


@product_bp.route("/product/<int:product_id>/add-to-cart", methods=["POST"])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    size_id = request.form.get("size_id", "").strip()
    try:
        quantity = max(1, int(request.form.get("quantity", "1")))
    except ValueError:
        quantity = 1

    size = ProductSize.query.filter_by(id=size_id, product_id=product.id).first()
    if not size:
        flash("Оберіть розмір", "error")
        return redirect(url_for("product.detail", product_id=product.id))

    cart = _get_cart()
    key = f"{product.id}:{size.id}"
    already_in_cart = cart.get(key, 0)

    if already_in_cart + quantity > size.quantity:
        available = max(size.quantity - already_in_cart, 0)
        if available <= 0:
            flash(f"Розмір {size.size} закінчився в кошику — більше додати не можна", "error")
        else:
            flash(f"У наявності лише {available} шт. розміру {size.size} понад те, що вже в кошику", "error")
        return redirect(url_for("product.detail", product_id=product.id))

    cart[key] = already_in_cart + quantity
    session.modified = True
    flash(f"«{product.name}» ({size.size}) додано в кошик", "success")
    return redirect(url_for("product.detail", product_id=product.id))


@product_bp.route("/cart")
def cart_view():
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

    return render_template("cart.html", items=items, total=total, form={})


@product_bp.route("/cart/remove", methods=["POST"])
def cart_remove():
    key = request.form.get("key", "")
    cart = _get_cart()
    if key in cart:
        del cart[key]
        session.modified = True
    return redirect(url_for("product.cart_view"))