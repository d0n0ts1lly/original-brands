from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Порядок розмірів для сортування (не алфавітний — інакше "L" опиняється
# перед "S", "XL" перед "M" тощо). Використовується і в каталозі, і на
# сторінці товару.
SIZE_ORDER = ["2XS", "XS", "S", "M", "L", "XL", "2XL", "3XL", "XXL"]


def size_sort_key(size):
    if size in SIZE_ORDER:
        return (0, SIZE_ORDER.index(size))
    # Розміри поза стандартним переліком (числові тощо) — у кінець.
    return (1, size)


class AdminUser(db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Category(db.Model):
    __tablename__ = "categories"
    __table_args__ = (
        db.UniqueConstraint("parent_id", "slug", name="uq_category_parent_slug"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), nullable=False)
    photo_url = db.Column(db.String(500), nullable=True)
    is_featured = db.Column(db.Boolean, nullable=False, default=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="CASCADE"), nullable=True)

    children = db.relationship(
        "Category",
        backref=db.backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
        order_by="Category.name",
    )
    products = db.relationship("Product", backref="category")

    @property
    def is_top_level(self):
        return self.parent_id is None


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    brand = db.Column(db.String(120), nullable=False)
    sku = db.Column(db.String(64), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_price = db.Column(db.Numeric(10, 2), nullable=True)
    is_featured_hit = db.Column(db.Boolean, nullable=False, default=False)
    is_featured_new = db.Column(db.Boolean, nullable=False, default=False)
    is_featured_sale = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sizes = db.relationship(
        "ProductSize", backref="product", cascade="all, delete-orphan",
        order_by="ProductSize.size",
    )
    colors = db.relationship(
        "ProductColor", backref="product", cascade="all, delete-orphan",
        order_by="ProductColor.sort_order",
    )
    photos = db.relationship(
        "ProductPhoto", backref="product", cascade="all, delete-orphan",
        order_by="ProductPhoto.sort_order",
    )

    @property
    def main_photo(self):
        for p in self.photos:
            if p.is_main:
                return p
        return self.photos[0] if self.photos else None

    @property
    def total_stock(self):
        return sum(s.quantity for s in self.sizes)

    @property
    def in_stock_sizes(self):
        return [s for s in self.sizes if s.quantity > 0]

    @property
    def has_colors(self):
        return len(self.colors) > 0

    @property
    def colors_in_stock(self):
        """Кольори, у яких є хоч один розмір у наявності — тільки такі
        показуємо перемикачем на сторінці товару."""
        return [c for c in self.colors if any(s.quantity > 0 for s in c.sizes)]

    @property
    def uncolored_sizes(self):
        """Розміри без прив'язки до кольору (звичайний товар без кольорів)."""
        return [s for s in self.sizes if s.color_id is None]

    @property
    def general_photos(self):
        """Фото без прив'язки до конкретного кольору."""
        return [p for p in self.photos if p.color_id is None]

    @property
    def display_photos(self):
        """Фото для початкового показу на сторінці товару (до вибору
        кольору): спершу загальні, якщо їх нема — фото першого кольору,
        якщо і того нема — взагалі все, що є."""
        if self.general_photos:
            return self.general_photos
        if self.colors and self.colors[0].photos:
            return self.colors[0].photos
        return self.photos

    @property
    def discount_percent(self):
        if not self.discount_price or not self.price:
            return None
        return round(100 - (float(self.discount_price) / float(self.price) * 100))

    @property
    def display_price(self):
        return self.discount_price if self.discount_price else self.price


class ProductColor(db.Model):
    __tablename__ = "product_colors"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(60), nullable=False)
    hex_value = db.Column(db.String(7), nullable=True)
    sort_order = db.Column(db.Integer, default=0)

    sizes = db.relationship(
        "ProductSize", backref="color", cascade="all, delete-orphan",
        order_by="ProductSize.size",
    )
    photos = db.relationship(
        "ProductPhoto", backref="color", cascade="all, delete-orphan",
        order_by="ProductPhoto.sort_order",
    )

    @property
    def in_stock_sizes(self):
        return sorted(
            [s for s in self.sizes if s.quantity > 0],
            key=lambda s: size_sort_key(s.size),
        )


class ProductSize(db.Model):
    __tablename__ = "product_sizes"
    __table_args__ = (
        db.UniqueConstraint(
            "product_id", "color_id", "size", name="uq_product_color_size"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    color_id = db.Column(
        db.Integer, db.ForeignKey("product_colors.id", ondelete="CASCADE"), nullable=True
    )
    size = db.Column(db.String(10), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)


class ProductPhoto(db.Model):
    __tablename__ = "product_photos"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    color_id = db.Column(
        db.Integer, db.ForeignKey("product_colors.id", ondelete="CASCADE"), nullable=True
    )
    url = db.Column(db.String(500), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    is_main = db.Column(db.Boolean, default=False)


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(120), nullable=False)
    np_branch = db.Column(db.String(255), nullable=False)
    np_ttn = db.Column(db.String(30), nullable=True)
    status = db.Column(
        db.Enum("new", "processing", "shipped", "completed", "cancelled",
                name="order_status"),
        default="new", nullable=False,
    )
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")

    @property
    def total(self):
        return sum(float(i.price) * i.quantity for i in self.items)


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    size_id = db.Column(db.Integer, db.ForeignKey("product_sizes.id"), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    product = db.relationship("Product")
    size = db.relationship("ProductSize")