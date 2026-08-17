from urllib.parse import urlencode

from flask import Blueprint, abort, make_response, render_template, request
from sqlalchemy import func, or_

from models import Category, Product, ProductSize, db

catalog_bp = Blueprint("catalog", __name__)

SORT_LABELS = {
    "newest": "Спочатку нові",
    "price_asc": "Дешевші спочатку",
    "price_desc": "Дорожчі спочатку",
    "name": "За назвою",
}

PAGE_SIZE = 20

# Порядок розмірів для фільтра — від найменшого до найбільшого,
# а не за алфавітом (інакше "L" опиняється перед "S", "XL" перед "M" тощо).
SIZE_ORDER = ["2XS", "XS", "S", "M", "L", "XL", "2XL", "3XL", "XXL"]


def _size_sort_key(size):
    if size in SIZE_ORDER:
        return (0, SIZE_ORDER.index(size))
    # Розміри поза стандартним переліком (наприклад, числові) —
    # у кінець списку, за власним алфавітним/числовим порядком.
    return (1, size)


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
    available_sizes = sorted({s.size for p in facet_products for s in p.sizes}, key=_size_sort_key)

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

    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1

    total_count = len(products)
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    page_products = products[start:end]
    has_more = end < total_count

    is_partial = request.headers.get("X-Requested-With") == "fetch"
    if is_partial:
        html = render_template("_product_cards_only.html", products=page_products)
        response = make_response(html)
        response.headers["X-Has-More"] = "1" if has_more else "0"
        return response

    # Для кнопки "Завантажити ще" — рядок поточних фільтрів без page,
    # щоб JS міг сам дописати наступну сторінку.
    filter_params = request.args.to_dict(flat=False)
    filter_params.pop("page", None)
    filters_query_string = urlencode(filter_params, doseq=True)

    return render_template(
        "catalog.html",
        products=page_products,
        total_count=total_count,
        has_more=has_more,
        next_page=page + 1,
        filters_query_string=filters_query_string,
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