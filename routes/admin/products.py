import re

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from models import Category, OrderItem, Product, ProductColor, ProductPhoto, ProductSize, db
from . import admin_bp
from ._uploads import save_uploaded_photo, delete_uploaded_photo

STANDARD_SIZES = ["2XS", "XS", "S", "M", "L", "XL", "2XL", "3XL"]
PHOTO_SUBFOLDER = "products"


def _save_uploaded_photo(file_storage):
    return save_uploaded_photo(file_storage, PHOTO_SUBFOLDER)


def _delete_uploaded_photo(url):
    delete_uploaded_photo(url)


def _collect_photo_entries(form, files, file_field="photo_file[]", url_field="photo_url[]"):
    """Збирає завантажені файли/URL з повторюваних рядків фото.
    file_field/url_field дозволяють перевикористати те саме для
    "загальних" фото товару і для фото конкретного кольору."""
    photo_files = files.getlist(file_field)
    photo_urls = form.getlist(url_field)
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


def _collect_color_entries(form, files):
    """Парсить кольори з форми. Поля іменовані з індексом кольору:
    color_name_<i>, color_id_<i> (тільки для вже існуючих кольорів,
    щоб знати — оновити чи створити), color_hex_<i>,
    color_size_<i>[] / color_qty_<i>[] (розміри саме цього кольору),
    color_photo_file_<i>[] / color_photo_url_<i>[] (фото цього кольору).

    Повертає список словників:
    {id, name, hex, sizes: [(size, qty), ...], photo_paths, photo_errors}
    у порядку, в якому кольори йшли у формі (= порядок на сторінці).
    """
    indices = set()
    for key in form.keys():
        m = re.match(r"^color_name_(\d+)$", key)
        if m:
            indices.add(int(m.group(1)))

    colors = []
    for i in sorted(indices):
        name = form.get(f"color_name_{i}", "").strip()
        if not name:
            continue

        color_id_raw = form.get(f"color_id_{i}", "").strip()
        color_id = int(color_id_raw) if color_id_raw.isdigit() else None

        hex_value = form.get(f"color_hex_{i}", "").strip() or None
        if hex_value and not re.match(r"^#[0-9a-fA-F]{6}$", hex_value):
            hex_value = None

        sizes_raw = form.getlist(f"color_size_{i}[]")
        qty_raw = form.getlist(f"color_qty_{i}[]")
        sizes = {}
        for s, q in zip(sizes_raw, qty_raw):
            s = s.strip().upper()
            if s:
                sizes[s] = int((q or "0").strip() or 0)

        photo_paths, photo_errors = _collect_photo_entries(
            form, files, f"color_photo_file_{i}[]", f"color_photo_url_{i}[]"
        )

        colors.append(
            {
                "id": color_id,
                "name": name,
                "hex": hex_value,
                "sizes": list(sizes.items()),
                "photo_paths": photo_paths,
                "photo_errors": photo_errors,
            }
        )

    return colors


def _delete_color_entry_photos(color_entries):
    """Прибирає з диску фото, щойно завантажені для кольорів у цьому
    запиті — використовується, коли форма зрештою не пройшла валідацію."""
    for c in color_entries:
        for path in c["photo_paths"]:
            _delete_uploaded_photo(path)


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


def _existing_colors_for_form(product):
    """Кольори товару у форматі, зручному для відмальовки в формі редагування."""
    colors = []
    for idx, c in enumerate(product.colors):
        colors.append(
            {
                "idx": idx,
                "id": c.id,
                "name": c.name,
                "hex": c.hex_value or "",
                "sizes": [(s.size, s.quantity) for s in c.sizes] or [("", "")],
                "photos": c.photos,
            }
        )
    return colors


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
            has_colors=False,
            existing_colors=[],
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

    has_colors = "has_colors" in form
    color_entries = _collect_color_entries(form, request.files) if has_colors else []

    photo_paths, photo_errors = _collect_photo_entries(form, request.files)

    category = Category.query.filter_by(id=category_id).first() if category_id else None

    errors = list(photo_errors)
    for c in color_entries:
        errors.extend(c["photo_errors"])

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

    if has_colors:
        if not color_entries:
            errors.append("Додайте хоча б один колір і вкажіть його назву")
        elif not any(c["sizes"] for c in color_entries):
            errors.append("Вкажіть розміри й кількість хоча б для одного кольору")
    else:
        if not size_pairs:
            errors.append("Вкажіть кількість хоча б для одного розміру")

    if errors:
        for e in errors:
            flash(e, "error")
        for path in photo_paths:
            _delete_uploaded_photo(path)
        _delete_color_entry_photos(color_entries)
        return render_template(
            "admin/product_form.html",
            form=form,
            std_sizes=STANDARD_SIZES,
            custom_rows=custom_rows,
            grouped_categories=_subcategories(),
            is_edit=False,
            existing_photos=[],
            has_colors=has_colors,
            existing_colors=color_entries,
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

        if has_colors:
            for i, entry in enumerate(color_entries):
                color = ProductColor(
                    product_id=product.id, name=entry["name"], hex_value=entry["hex"], sort_order=i
                )
                db.session.add(color)
                db.session.flush()
                for size, qty in entry["sizes"]:
                    db.session.add(
                        ProductSize(product_id=product.id, color_id=color.id, size=size, quantity=qty)
                    )
                for j, path in enumerate(entry["photo_paths"]):
                    db.session.add(
                        ProductPhoto(
                            product_id=product.id, color_id=color.id, url=path,
                            sort_order=j, is_main=False,
                        )
                    )
        else:
            for size, qty in size_pairs:
                db.session.add(ProductSize(product_id=product.id, size=size, quantity=qty))

        for i, path in enumerate(photo_paths):
            db.session.add(ProductPhoto(product_id=product.id, url=path, sort_order=i, is_main=(i == 0)))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        for path in photo_paths:
            _delete_uploaded_photo(path)
        _delete_color_entry_photos(color_entries)
        flash(f"Артикул «{sku}» вже використовується — вкажіть інший", "error")
        return render_template(
            "admin/product_form.html",
            form=form,
            std_sizes=STANDARD_SIZES,
            custom_rows=custom_rows,
            grouped_categories=_subcategories(),
            is_edit=False,
            existing_photos=[],
            has_colors=has_colors,
            existing_colors=color_entries,
        ), 400

    flash(f"Товар «{product.name}» додано", "success")
    return redirect(url_for("admin.products_list"))


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
def product_edit(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == "GET":
        std_pairs = [(s.size, s.quantity) for s in product.uncolored_sizes if s.size in STANDARD_SIZES]
        custom_pairs = [(s.size, s.quantity) for s in product.uncolored_sizes if s.size not in STANDARD_SIZES]
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
            existing_photos=product.general_photos,
            has_colors=product.has_colors,
            existing_colors=_existing_colors_for_form(product),
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

    has_colors = "has_colors" in form
    color_entries = _collect_color_entries(form, request.files) if has_colors else []

    new_photo_paths, photo_errors = _collect_photo_entries(form, request.files)
    delete_photo_ids = {int(x) for x in form.getlist("delete_photo[]") if x.isdigit()}

    category = Category.query.filter_by(id=category_id).first() if category_id else None

    errors = list(photo_errors)
    for c in color_entries:
        errors.extend(c["photo_errors"])

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

    if has_colors:
        if not color_entries:
            errors.append("Додайте хоча б один колір і вкажіть його назву")
        elif not any(c["sizes"] for c in color_entries):
            errors.append("Вкажіть розміри й кількість хоча б для одного кольору")
    else:
        if not size_pairs:
            errors.append("Вкажіть кількість хоча б для одного розміру")

    if errors:
        for e in errors:
            flash(e, "error")
        for path in new_photo_paths:
            _delete_uploaded_photo(path)
        _delete_color_entry_photos(color_entries)
        return render_template(
            "admin/product_form.html",
            form=form,
            std_sizes=STANDARD_SIZES,
            custom_rows=custom_rows,
            grouped_categories=_subcategories(),
            is_edit=True,
            product=product,
            existing_photos=product.general_photos,
            has_colors=has_colors,
            existing_colors=color_entries,
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

    # Розміри/кольори/їхні фото: оновлюємо/додаємо потрібне, видаляємо
    # зайве — але не чіпаємо розмір, якщо на нього вже є замовлення
    # (історію не ламаємо).
    skipped_removals = []

    if has_colors:
        existing_colors_by_id = {c.id: c for c in product.colors}
        submitted_color_ids = {c["id"] for c in color_entries if c["id"]}

        for cid, color in list(existing_colors_by_id.items()):
            if cid not in submitted_color_ids:
                size_ids = [s.id for s in color.sizes]
                has_orders = (
                    size_ids
                    and OrderItem.query.filter(OrderItem.size_id.in_(size_ids)).first() is not None
                )
                if has_orders:
                    skipped_removals.append(f"колір «{color.name}»")
                else:
                    for photo in color.photos:
                        _delete_uploaded_photo(photo.url)
                    db.session.delete(color)

        for i, entry in enumerate(color_entries):
            if entry["id"] and entry["id"] in existing_colors_by_id:
                color = existing_colors_by_id[entry["id"]]
                color.name = entry["name"]
                color.hex_value = entry["hex"]
                color.sort_order = i
            else:
                color = ProductColor(
                    product_id=product.id, name=entry["name"], hex_value=entry["hex"], sort_order=i
                )
                db.session.add(color)
                db.session.flush()

            existing_sizes_by_size = {s.size: s for s in color.sizes}
            submitted_sizes = dict(entry["sizes"])

            for size, qty in submitted_sizes.items():
                if size in existing_sizes_by_size:
                    existing_sizes_by_size[size].quantity = qty
                else:
                    db.session.add(
                        ProductSize(product_id=product.id, color_id=color.id, size=size, quantity=qty)
                    )

            for size, existing_size in existing_sizes_by_size.items():
                if size not in submitted_sizes:
                    has_orders = OrderItem.query.filter_by(size_id=existing_size.id).first() is not None
                    if has_orders:
                        skipped_removals.append(f"{color.name} {size}")
                    else:
                        db.session.delete(existing_size)

            # Нові фото саме цього кольору (видалення старих — нижче,
            # разом із загальними фото, через спільний delete_photo[])
            next_photo_sort = (max((p.sort_order for p in color.photos), default=-1)) + 1
            for j, path in enumerate(entry["photo_paths"]):
                db.session.add(
                    ProductPhoto(
                        product_id=product.id, color_id=color.id, url=path,
                        sort_order=next_photo_sort + j, is_main=False,
                    )
                )

        # Товар щойно став "кольоровим" — прибираємо старі безкольорові
        # розміри, якщо на них нема замовлень.
        for s in product.uncolored_sizes:
            has_orders = OrderItem.query.filter_by(size_id=s.id).first() is not None
            if has_orders:
                skipped_removals.append(s.size)
            else:
                db.session.delete(s)
    else:
        existing_by_size = {s.size: s for s in product.uncolored_sizes}

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

        # Товар більше не "кольоровий" — прибираємо старі кольори (і їх
        # розміри та фото), якщо на них нема замовлень.
        for color in list(product.colors):
            size_ids = [s.id for s in color.sizes]
            has_orders = (
                size_ids
                and OrderItem.query.filter(OrderItem.size_id.in_(size_ids)).first() is not None
            )
            if has_orders:
                skipped_removals.append(f"колір «{color.name}»")
            else:
                for photo in color.photos:
                    _delete_uploaded_photo(photo.url)
                db.session.delete(color)

    if skipped_removals:
        flash(
            "Не видалено (вже є замовлення): " + ", ".join(skipped_removals) +
            ". Можна виставити кількість 0.",
            "error",
        )

    # Фото: видаляємо позначені (і загальні, і кольорові — той самий
    # чекбокс delete_photo[] працює для обох), додаємо нові загальні
    remaining_general_photos = []
    for photo in list(product.photos):
        if photo.id in delete_photo_ids:
            _delete_uploaded_photo(photo.url)
            db.session.delete(photo)
        elif photo.color_id is None:
            remaining_general_photos.append(photo)

    next_sort = (max((p.sort_order for p in remaining_general_photos), default=-1)) + 1
    for i, path in enumerate(new_photo_paths):
        db.session.add(ProductPhoto(product_id=product.id, url=path, sort_order=next_sort + i, is_main=False))

    try:
        db.session.flush()
        general_photos = [p for p in product.photos if p.color_id is None]
        still_has_main = any(p.is_main for p in general_photos)
        if not still_has_main and general_photos:
            ordered = sorted(general_photos, key=lambda p: p.sort_order)
            ordered[0].is_main = True
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        for path in new_photo_paths:
            _delete_uploaded_photo(path)
        _delete_color_entry_photos(color_entries)
        flash(f"Артикул «{sku}» вже використовується іншим товаром", "error")
        return render_template(
            "admin/product_form.html",
            form=form,
            std_sizes=STANDARD_SIZES,
            custom_rows=custom_rows,
            grouped_categories=_subcategories(),
            is_edit=True,
            product=product,
            existing_photos=product.general_photos,
            has_colors=has_colors,
            existing_colors=color_entries,
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