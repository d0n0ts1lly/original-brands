from flask import Blueprint, abort, render_template, request
from sqlalchemy import func, or_

from models import Category, Product, ProductSize, db

catalog_bp = Blueprint("catalog", __name__)

SORT_LABELS = {
    "newest": "Спочатку нові",
    "price_asc": "Дешевші спочатку",
    "price_desc": "Дорожчі спочатку",
    "name": "За назвою",
}


@catalog_bp.route("/catalog")
@catalog_bp.route("/catalog/<cat_slug>")
@catalog_bp.route("/catalog/<cat_slug>/<sub_slug>")
def catalog(cat_slug=None, sub_slug=None):
    active_category = None
    active_sub = None
    category_scope_ids = None

    if cat_slug:
        active_category = Category.query.filter_by(slug=cat_slug, parent_id=None).first()
        if not active_category:
            abort(404)
        if sub_slug:
            active_sub = Category.query.filter_by(slug=sub_slug, parent_id=active_category.id).first()
            if not active_sub:
                abort(404)
            category_scope_ids = [active_sub.id]
        else:
            category_scope_ids = [c.id for c in active_category.children] or [-1]

    base_query = Product.query
    if category_scope_ids is not None:
        base_query = base_query.filter(Product.category_id.in_(category_scope_ids))

    # Фасети рахуємо по товарах категорії, без урахування пошуку/фільтрів —
    # щоб чекбокси не "стрибали", поки людина щось вибирає.
    facet_products = base_query.all()
    available_brands = sorted({p.brand for p in facet_products})
    available_sizes = sorted({s.size for p in facet_products for s in p.sizes})

    effective_price = func.coalesce(Product.discount_price, Product.price)
    query = base_query

    q = request.args.get("q", "").strip()
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Product.name.ilike(like), Product.brand.ilike(like), Product.sku.ilike(like)))

    selected_brands = request.args.getlist("brand")
    if selected_brands:
        query = query.filter(Product.brand.in_(selected_brands))

    selected_sizes = request.args.getlist("size")
    if selected_sizes:
        query = (
            query.join(ProductSize)
            .filter(ProductSize.size.in_(selected_sizes), ProductSize.quantity > 0)
            .distinct()
        )

    price_min = request.args.get("price_min", type=float)
    price_max = request.args.get("price_max", type=float)
    if price_min is not None:
        query = query.filter(effective_price >= price_min)
    if price_max is not None:
        query = query.filter(effective_price <= price_max)

    sort = request.args.get("sort", "newest")
    if sort == "price_asc":
        query = query.order_by(effective_price.asc())
    elif sort == "price_desc":
        query = query.order_by(effective_price.desc())
    elif sort == "name":
        query = query.order_by(Product.name.asc())
    else:
        sort = "newest"
        query = query.order_by(Product.created_at.desc())

    products = query.all()

    return render_template(
        "catalog.html",
        products=products,
        active_category=active_category,
        active_sub=active_sub,
        available_brands=available_brands,
        available_sizes=available_sizes,
        selected_brands=selected_brands,
        selected_sizes=selected_sizes,
        price_min=request.args.get("price_min", ""),
        price_max=request.args.get("price_max", ""),
        q=q,
        sort=sort,
        sort_labels=SORT_LABELS,
    )