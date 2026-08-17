from flask import flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from models import Category, OrderItem, Product, ProductPhoto, ProductSize, db
from . import admin_bp
from ._uploads import save_uploaded_photo, delete_uploaded_photo

STANDARD_SIZES = ["2XS", "XS", "S", "M", "L", "XL", "2XL", "3XL"]
PHOTO_SUBFOLDER = "products"


def _save_uploaded_photo(file_storage):
    return save_uploaded_photo(file_storage, PHOTO_SUBFOLDER)


def _delete_uploaded_photo(url):
    delete_uploaded_photo(url)


def _collect_photo_entries(form, files):
    photo_files = files.getlist("photo_file[]")
    photo_urls = form.getlist("photo_url[]")
    total_rows = max(len(photo_files), len(photo_urls))

    saved_paths = []
    errors = []

    for i in range(total_rows):
        file_storage = photo_files[i] if i < len(photo_files) else None
        url_value = photo_urls[i].strip() if i < len(photo_urls) else ""

        if file_storage and file_storage.filename:
            path, err = _save_uploaded_photo(file_storage)
            if err:
                errors.append(err)
                continue
            saved_paths.append(path)
        elif url_value:
            saved_paths.append(url_value)

    return saved_paths, errors


def _collect_size_pairs(form):
    sizes = {}

    for sz in STANDARD_SIZES:
        raw = form.get(f"qty_{sz}", "").strip()
        if raw != "":
            sizes[sz] = int(raw)

    custom_sizes = form.getlist("size[]")
    custom_qty = form.getlist("quantity[]")
    for s, q in zip(custom_sizes, custom_qty):
        s = s.strip().upper()
        if s:
            sizes[s] = int((q or "0").strip() or 0)

    return list(sizes.items())


def _subcategories():
    top_levels = Category.query.filter_by(parent_id=None).order_by(Category.name).all()
    return [(top, top.children) for top in top_levels]


def _size_rows_for_form(std_pairs, custom_pairs):
    """Розкладає збережені розміри товару назад по формі: стандартні -> qty_XX, решта -> кастомні рядки."""
    std_qty = {}
    custom_rows = []
    for size, qty in std_pairs + custom_pairs:
        if size in STANDARD_SIZES:
            std_qty[size] = qty
        else:
            custom_rows.append((size, qty))
    return std_qty, custom_rows or [("", "")]


@admin_bp.route("/products")
def products_list():
    products = Product.query.order_by(Product.id.desc()).all()
    return render_template("admin/products_list.html", products=products)


@admin_bp.route("/products/new", methods=["GET", "POST"])
def product_new():
    if request.method == "GET":
        return render_template(
            "admin/product_form.html",
            form={},
            std_sizes=STANDARD_SIZES,
            custom_rows=[("", "")],
            grouped_categories=_subcategories(),
            is_edit=False,
            existing_photos=[],
        )

    form = request.form
    name = form.get("name", "").strip()
    brand = form.get("brand", "").strip()
    sku = form.get("sku", "").strip()
    description = form.get("description", "").strip()
    price = form.get("price", "").strip()
    discount_price = form.get("discount_price", "").strip()
    category_id = form.get("category_id", "").strip()

    custom_rows = list(zip(form.getlist("size[]"), form.getlist("quantity[]"))) or [("", "")]
    size_pairs = _collect_size_pairs(form)
    photo_paths, photo_errors = _collect_photo_entries(form, request.files)

    category = Category.query.filter_by(id=category_id).first() if category_id else None

    errors = list(photo_errors)
    if not name:
        errors.append("Вкажіть назву товару")
    if not brand:
        errors.append("Вкажіть бренд")
    if not sku:
        errors.append("Вкажіть артикул")
    if not price:
        errors.append("Вкажіть базову ціну")
    if not category or category.parent_id is None:
        errors.append("Виберіть підкатегорію товару")
    if not size_pairs:
        errors.append("Вкажіть кількість хоча б для одного розміру")

    if errors:
        for e in errors:
            flash(e, "error")
        return render_template(
            "admin/product_form.html",
            form=form,
            std_sizes=STANDARD_SIZES,
            custom_rows=custom_rows,
            grouped_categories=_subcategories(),
            is_edit=False,
            existing_photos=[],
        ), 400

    product = Product(
        name=name, brand=brand, sku=sku, description=description or None,
        price=price, discount_price=discount_price or None,
        category_id=category.id,
        is_featured_hit="is_featured_hit" in form,
        is_featured_new="is_featured_new" in form,
        is_featured_sale="is_featured_sale" in form,
    )
    db.session.add(product)

    try:
        db.session.flush()
        for size, qty in size_pairs:
            db.session.add(ProductSize(product_id=product.id, size=size, quantity=qty))
        for i, path in enumerate(photo_paths):
            db.session.add(ProductPhoto(product_id=product.id, url=path, sort_order=i, is_main=(i == 0)))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        for path in photo_paths:
            _delete_uploaded_photo(path)
        flash(f"Артикул «{sku}» вже використовується — вкажіть інший", "error")
        return render_template(
            "admin/product_form.html",
            form=form,
            std_sizes=STANDARD_SIZES,
            custom_rows=custom_rows,
            grouped_categories=_subcategories(),
            is_edit=False,
            existing_photos=[],
        ), 400

    flash(f"Товар «{product.name}» додано", "success")
    return redirect(url_for("admin.products_list"))


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
def product_edit(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == "GET":
        std_pairs = [(s.size, s.quantity) for s in product.sizes if s.size in STANDARD_SIZES]
        custom_pairs = [(s.size, s.quantity) for s in product.sizes if s.size not in STANDARD_SIZES]
        std_qty, custom_rows = _size_rows_for_form(std_pairs, custom_pairs)
        form = {
            "name": product.name, "brand": product.brand, "sku": product.sku,
            "description": product.description or "", "price": str(product.price),
            "discount_price": str(product.discount_price) if product.discount_price else "",
            "category_id": str(product.category_id),
            "is_featured_hit": product.is_featured_hit,
            "is_featured_new": product.is_featured_new,
            "is_featured_sale": product.is_featured_sale,
            **{f"qty_{sz}": str(std_qty[sz]) for sz in std_qty},
        }
        return render_template(
            "admin/product_form.html",
            form=form,
            std_sizes=STANDARD_SIZES,
            custom_rows=custom_rows,
            grouped_categories=_subcategories(),
            is_edit=True,
            product=product,
            existing_photos=product.photos,
        )

    form = request.form
    name = form.get("name", "").strip()
    brand = form.get("brand", "").strip()
    sku = form.get("sku", "").strip()
    description = form.get("description", "").strip()
    price = form.get("price", "").strip()
    discount_price = form.get("discount_price", "").strip()
    category_id = form.get("category_id", "").strip()

    custom_rows = list(zip(form.getlist("size[]"), form.getlist("quantity[]"))) or [("", "")]
    size_pairs = dict(_collect_size_pairs(form))
    new_photo_paths, photo_errors = _collect_photo_entries(form, request.files)
    delete_photo_ids = {int(x) for x in form.getlist("delete_photo[]") if x.isdigit()}

    category = Category.query.filter_by(id=category_id).first() if category_id else None

    errors = list(photo_errors)
    if not name:
        errors.append("Вкажіть назву товару")
    if not brand:
        errors.append("Вкажіть бренд")
    if not sku:
        errors.append("Вкажіть артикул")
    if not price:
        errors.append("Вкажіть базову ціну")
    if not category or category.parent_id is None:
        errors.append("Виберіть підкатегорію товару")
    if not size_pairs:
        errors.append("Вкажіть кількість хоча б для одного розміру")

    if errors:
        for e in errors:
            flash(e, "error")
        for path in new_photo_paths:
            _delete_uploaded_photo(path)
        return render_template(
            "admin/product_form.html",
            form=form,
            std_sizes=STANDARD_SIZES,
            custom_rows=custom_rows,
            grouped_categories=_subcategories(),
            is_edit=True,
            product=product,
            existing_photos=product.photos,
        ), 400

    product.name = name
    product.brand = brand
    product.sku = sku
    product.description = description or None
    product.price = price
    product.discount_price = discount_price or None
    product.category_id = category.id
    product.is_featured_hit = "is_featured_hit" in form
    product.is_featured_new = "is_featured_new" in form
    product.is_featured_sale = "is_featured_sale" in form

    # Розміри: оновлюємо/додаємо потрібні, видаляємо зайві —
    # але не чіпаємо розмір, якщо на нього вже є замовлення (історію не ламаємо).
    existing_by_size = {s.size: s for s in product.sizes}
    skipped_removals = []

    for size, qty in size_pairs.items():
        if size in existing_by_size:
            existing_by_size[size].quantity = qty
        else:
            db.session.add(ProductSize(product_id=product.id, size=size, quantity=qty))

    for size, existing in existing_by_size.items():
        if size not in size_pairs:
            has_orders = OrderItem.query.filter_by(size_id=existing.id).first() is not None
            if has_orders:
                skipped_removals.append(size)
            else:
                db.session.delete(existing)

    if skipped_removals:
        flash(
            "Розмір(и) " + ", ".join(skipped_removals) +
            " не видалено — на них уже є замовлення. Можна виставити кількість 0.",
            "error",
        )

    # Фото: видаляємо позначені, додаємо нові
    remaining_photos = []
    for photo in list(product.photos):
        if photo.id in delete_photo_ids:
            _delete_uploaded_photo(photo.url)
            db.session.delete(photo)
        else:
            remaining_photos.append(photo)

    next_sort = (max((p.sort_order for p in remaining_photos), default=-1)) + 1
    for i, path in enumerate(new_photo_paths):
        db.session.add(ProductPhoto(product_id=product.id, url=path, sort_order=next_sort + i, is_main=False))

    try:
        db.session.flush()
        still_has_main = any(p.is_main for p in product.photos)
        if not still_has_main and product.photos:
            ordered = sorted(product.photos, key=lambda p: p.sort_order)
            ordered[0].is_main = True
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        for path in new_photo_paths:
            _delete_uploaded_photo(path)
        flash(f"Артикул «{sku}» вже використовується іншим товаром", "error")
        return render_template(
            "admin/product_form.html",
            form=form,
            std_sizes=STANDARD_SIZES,
            custom_rows=custom_rows,
            grouped_categories=_subcategories(),
            is_edit=True,
            product=product,
            existing_photos=product.photos,
        ), 400

    flash(f"Товар «{product.name}» оновлено", "success")
    return redirect(url_for("admin.products_list"))


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
def product_delete(product_id):
    product = Product.query.get_or_404(product_id)

    has_orders = (
        OrderItem.query.filter_by(product_id=product.id).first() is not None
    )
    if has_orders:
        flash(
            f"Товар «{product.name}» не можна видалити — на нього вже є замовлення. "
            "Можна виставити всі кількості в 0, щоб прибрати з продажу.",
            "error",
        )
        return redirect(url_for("admin.products_list"))

    for photo in product.photos:
        _delete_uploaded_photo(photo.url)
    db.session.delete(product)
    db.session.commit()
    flash(f"Товар «{product.name}» видалено", "success")
    return redirect(url_for("admin.products_list"))