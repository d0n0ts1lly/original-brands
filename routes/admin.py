import os
import uuid

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from slugify import slugify
from sqlalchemy.exc import IntegrityError

from models import Category, Product, ProductPhoto, ProductSize, db

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")

STANDARD_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]
ALLOWED_PHOTO_EXT = {"png", "jpg", "jpeg", "webp", "gif"}


@admin_bp.before_request
def require_login():
    if "admin_id" not in session:
        return redirect(url_for("auth.login", next=request.path))


@admin_bp.route("/")
def dashboard():
    return redirect(url_for("admin.products_list"))


def _save_uploaded_photo(file_storage):
    """Зберігає файл у static/uploads/products і повертає публічний шлях."""
    filename = file_storage.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_PHOTO_EXT:
        return None, f"Непідтримуваний формат файлу «{filename}»"

    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "products")
    os.makedirs(upload_dir, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(upload_dir, stored_name))
    return f"/static/uploads/products/{stored_name}", None


def _collect_photo_entries(form, files):
    """Пара за парою: файл із комп'ютера має пріоритет над посиланням у тому ж рядку."""
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
    """Стандартні розміри (XS…XXL) + довільні (наприклад, числові для джинсів)."""
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
    """Підкатегорії, згруповані по головній категорії — для <optgroup>."""
    top_levels = Category.query.filter_by(parent_id=None).order_by(Category.name).all()
    return [(top, top.children) for top in top_levels]


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
        # завантажені файли на диску лишаться сиротами при повторній помилці —
        # прийнятний компроміс для MVP, приберемо разом з чергою фонових задач пізніше
        return render_template(
            "admin/product_form.html",
            form=form,
            std_sizes=STANDARD_SIZES,
            custom_rows=custom_rows,
            grouped_categories=_subcategories(),
        ), 400

    product = Product(
        name=name, brand=brand, sku=sku, description=description or None,
        price=price, discount_price=discount_price or None,
        category_id=category.id,
    )
    db.session.add(product)

    try:
        db.session.flush()

        for size, qty in size_pairs:
            db.session.add(ProductSize(product_id=product.id, size=size, quantity=qty))

        for i, path in enumerate(photo_paths):
            db.session.add(
                ProductPhoto(product_id=product.id, url=path, sort_order=i, is_main=(i == 0))
            )

        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        for path in photo_paths:
            if path.startswith("/static/uploads/"):
                full = os.path.join(current_app.root_path, path.lstrip("/"))
                if os.path.exists(full):
                    os.remove(full)
        flash(f"Артикул «{sku}» вже використовується — вкажіть інший", "error")
        return render_template(
            "admin/product_form.html",
            form=form,
            std_sizes=STANDARD_SIZES,
            custom_rows=custom_rows,
            grouped_categories=_subcategories(),
        ), 400

    flash(f"Товар «{product.name}» додано", "success")
    return redirect(url_for("admin.products_list"))


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
def product_delete(product_id):
    product = Product.query.get_or_404(product_id)
    for photo in product.photos:
        if photo.url.startswith("/static/uploads/"):
            full = os.path.join(current_app.root_path, photo.url.lstrip("/"))
            if os.path.exists(full):
                os.remove(full)
    db.session.delete(product)
    db.session.commit()
    flash(f"Товар «{product.name}» видалено", "success")
    return redirect(url_for("admin.products_list"))


@admin_bp.route("/categories")
def categories_list():
    top_levels = Category.query.filter_by(parent_id=None).order_by(Category.name).all()
    return render_template("admin/categories.html", top_levels=top_levels)


@admin_bp.route("/categories/new", methods=["POST"])
def category_new():
    name = request.form.get("name", "").strip()
    parent_id = request.form.get("parent_id", "").strip()

    if not name:
        flash("Вкажіть назву категорії", "error")
        return redirect(url_for("admin.categories_list"))

    parent = None
    if parent_id:
        parent = Category.query.get(parent_id)
        if not parent or parent.parent_id is not None:
            flash("Оберіть коректну головну категорію", "error")
            return redirect(url_for("admin.categories_list"))

    category = Category(name=name, slug=slugify(name), parent_id=parent.id if parent else None)
    db.session.add(category)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(f"Категорія «{name}» вже існує в цьому розділі", "error")
        return redirect(url_for("admin.categories_list"))

    kind = "Підкатегорію" if parent else "Категорію"
    flash(f"{kind} «{name}» додано", "success")
    return redirect(url_for("admin.categories_list"))