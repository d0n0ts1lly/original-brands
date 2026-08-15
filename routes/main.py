from flask import Blueprint, render_template
from sqlalchemy import func

from models import Category, OrderItem, Product, db

main_bp = Blueprint("main", __name__)

CATEGORY_ICONS = {
    "худі": "fa-vest-patches",
    "футболки": "fa-shirt",
    "джинси": "fa-socks",
    "куртки": "fa-vest",
}
SHOWCASE_LIMIT = 8


def _icon_for(name):
    return CATEGORY_ICONS.get(name.strip().lower(), "fa-shirt")


def _featured_categories():
    """Категорії на плитках — те, що адмін позначив «показувати на головній».
    Якщо ще нічого не позначено, підбираємо автоматично (найбільш заповнені),
    щоб головна сторінка не була порожньою одразу після встановлення."""
    manual = (
        Category.query.filter(Category.parent_id.isnot(None), Category.is_featured.is_(True))
        .order_by(Category.name)
        .limit(4)
        .all()
    )
    if manual:
        return manual

    rows = (
        db.session.query(Category, func.count(Product.id))
        .outerjoin(Product, Product.category_id == Category.id)
        .filter(Category.parent_id.isnot(None))
        .group_by(Category.id)
        .order_by(func.count(Product.id).desc(), Category.name)
        .limit(4)
        .all()
    )
    return [c for c, _ in rows]


def _section_products(flag_column, fallback_query):
    manual = (
        Product.query.filter(flag_column.is_(True))
        .order_by(Product.created_at.desc())
        .limit(SHOWCASE_LIMIT)
        .all()
    )
    return manual if manual else fallback_query.limit(SHOWCASE_LIMIT).all()


@main_bp.route("/")
def index():
    benefits = [
        {"icon": "truck", "title": "Швидка доставка", "text": "1–2 дні по всій Україні"},
        {"icon": "return", "title": "Легке повернення", "text": "14 днів на обмін без питань"},
        {"icon": "cash", "title": "Оплата при отриманні", "text": "Перевіряєте замовлення перед оплатою"},
        {"icon": "check", "title": "100% оригінал", "text": "Сертифікати на кожну позицію"},
    ]

    featured = _featured_categories()
    counts = {}
    if featured:
        counts = dict(
            db.session.query(Product.category_id, func.count(Product.id))
            .filter(Product.category_id.in_([c.id for c in featured]))
            .group_by(Product.category_id)
            .all()
        )
    categories = [
        {"category": c, "count": counts.get(c.id, 0), "icon": _icon_for(c.name)}
        for c in featured
    ]

    new_products = _section_products(
        Product.is_featured_new,
        Product.query.order_by(Product.created_at.desc()),
    )

    sale_products = _section_products(
        Product.is_featured_sale,
        Product.query.filter(Product.discount_price.isnot(None)).order_by(Product.created_at.desc()),
    )

    hits_manual = (
        Product.query.filter(Product.is_featured_hit.is_(True))
        .order_by(Product.created_at.desc())
        .limit(SHOWCASE_LIMIT)
        .all()
    )
    if hits_manual:
        hits_products = hits_manual
    else:
        hits_rows = (
            db.session.query(Product, func.sum(OrderItem.quantity))
            .outerjoin(OrderItem, OrderItem.product_id == Product.id)
            .group_by(Product.id)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(SHOWCASE_LIMIT)
            .all()
        )
        hits_auto = [p for p, sold in hits_rows if sold]
        hits_products = hits_auto if hits_auto else new_products

    return render_template(
        "index.html",
        benefits=benefits,
        categories=categories,
        products={"hits": hits_products, "new": new_products, "sale": sale_products},
    )