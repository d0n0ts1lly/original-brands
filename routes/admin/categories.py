from flask import flash, redirect, render_template, request, url_for
from slugify import slugify
from sqlalchemy.exc import IntegrityError

from models import Category, Product, db
from . import admin_bp
from ._uploads import save_uploaded_photo, delete_uploaded_photo

PHOTO_SUBFOLDER = "categories"


def _photo_from_request(form, files):
    """Файл із комп'ютера має пріоритет над посиланням."""
    photo_file = files.get("photo_file")
    photo_url_input = form.get("photo_url", "").strip()

    if photo_file and photo_file.filename:
        path, err = save_uploaded_photo(photo_file, PHOTO_SUBFOLDER)
        if err:
            return None, err
        return path, None
    if photo_url_input:
        return photo_url_input, None
    return None, None


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

    photo_url, photo_err = _photo_from_request(request.form, request.files)
    if photo_err:
        flash(photo_err, "error")
        return redirect(url_for("admin.categories_list"))

    category = Category(
        name=name, slug=slugify(name), parent_id=parent.id if parent else None,
        photo_url=photo_url, is_featured=request.form.get("is_featured") == "1",
    )
    db.session.add(category)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if photo_url:
            delete_uploaded_photo(photo_url)
        flash(f"Категорія «{name}» вже існує в цьому розділі", "error")
        return redirect(url_for("admin.categories_list"))

    kind = "Підкатегорію" if parent else "Категорію"
    flash(f"{kind} «{name}» додано", "success")
    return redirect(url_for("admin.categories_list"))


@admin_bp.route("/categories/<int:category_id>/edit", methods=["POST"])
def category_edit(category_id):
    category = Category.query.get_or_404(category_id)
    name = request.form.get("name", "").strip()
    parent_id = request.form.get("parent_id", "").strip()
    remove_photo = request.form.get("remove_photo") == "1"

    if not name:
        flash("Вкажіть назву категорії", "error")
        return redirect(url_for("admin.categories_list"))

    new_parent_id = None
    if category.parent_id is not None:
        if parent_id:
            parent = Category.query.get(parent_id)
            if not parent or parent.parent_id is not None:
                flash("Оберіть коректну головну категорію", "error")
                return redirect(url_for("admin.categories_list"))
            new_parent_id = parent.id
        else:
            flash("Підкатегорія має належати якомусь розділу", "error")
            return redirect(url_for("admin.categories_list"))

    new_photo_url, photo_err = _photo_from_request(request.form, request.files)
    if photo_err:
        flash(photo_err, "error")
        return redirect(url_for("admin.categories_list"))

    old_photo_url = category.photo_url

    category.name = name
    category.slug = slugify(name)
    category.parent_id = new_parent_id if category.parent_id is not None else None
    category.is_featured = request.form.get("is_featured") == "1"

    if new_photo_url:
        category.photo_url = new_photo_url
    elif remove_photo:
        category.photo_url = None

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if new_photo_url:
            delete_uploaded_photo(new_photo_url)
        flash(f"Категорія «{name}» вже існує в цьому розділі", "error")
        return redirect(url_for("admin.categories_list"))

    # старе фото прибираємо з диска лише після успішного коміту
    if (new_photo_url or remove_photo) and old_photo_url and old_photo_url != category.photo_url:
        delete_uploaded_photo(old_photo_url)

    flash(f"Категорію «{name}» оновлено", "success")
    return redirect(url_for("admin.categories_list"))


@admin_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
def category_delete(category_id):
    category = Category.query.get_or_404(category_id)

    affected_ids = [category.id] + [c.id for c in category.children]
    has_products = Product.query.filter(Product.category_id.in_(affected_ids)).first() is not None

    if has_products:
        flash(
            f"«{category.name}» не можна видалити — у ній (або підкатегоріях) є товари. "
            "Спершу перенесіть або видаліть ці товари.",
            "error",
        )
        return redirect(url_for("admin.categories_list"))

    name = category.name
    photo_url = category.photo_url
    child_photos = [c.photo_url for c in category.children if c.photo_url]

    db.session.delete(category)
    db.session.commit()

    if photo_url:
        delete_uploaded_photo(photo_url)
    for p in child_photos:
        delete_uploaded_photo(p)

    flash(f"«{name}» видалено", "success")
    return redirect(url_for("admin.categories_list"))