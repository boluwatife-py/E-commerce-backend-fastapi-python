from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, DECIMAL, Date, CheckConstraint, Boolean, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    role = Column(String(20), nullable=False, default="buyer")
    created_at = Column(TIMESTAMP, server_default=func.now())

    data = relationship("UserData", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # Relationships with other tables
    product = relationship("Product", back_populates="seller", cascade="all, delete", lazy="dynamic")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")
    wishlists = relationship("Wishlist", back_populates="user", cascade="all, delete-orphan")
    cart = relationship("Cart", back_populates="user", cascade="all, delete-orphan")
    verification_tokens = relationship("VerificationToken", back_populates="user")
    otps = relationship("Otp", back_populates="user")

    reports_received = relationship(
        "ProductReport",
        foreign_keys='[ProductReport.seller_id]',
        back_populates="reported_seller"
    )

    reports_made = relationship(
        "ProductReport",
        foreign_keys='[ProductReport.user_id]',
        back_populates="reported_by"
    )

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'buyer', 'merchant')", name="check_user_role"),
    )

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class UserData(Base):
    __tablename__ = "user_data"

    profile_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False)

    phone = Column(String(20), unique=True, nullable=False)
    address = Column(Text, nullable=True)
    city = Column(String(50), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(10), nullable=True)
    country = Column(String(50), nullable=True)

    user = relationship("User", back_populates="data")

    def __repr__(self):
        return f"<UserData{self.user_id}>"

    
class Product(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=True)
    description = Column(Text)
    price = Column(DECIMAL(10, 2), nullable=True)
    stock_quantity = Column(Integer, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.category_id", ondelete="SET NULL"), nullable=True)
    seller_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    brand = Column(String(100))
    status = Column(String, default='draft', nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    currency_code = Column(String(3), ForeignKey('currencies.code'), nullable=True)

    currency = relationship('Currency', back_populates='products')
    category = relationship("Category", back_populates="product")
    seller = relationship("User", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")
    reviews = relationship("Review", back_populates="product", cascade="all, delete-orphan")
    wishlists = relationship("Wishlist", back_populates="product", cascade="all, delete-orphan")
    cart = relationship("Cart", back_populates="product", cascade="all, delete-orphan")
    product_images = relationship("ProductImages", back_populates="product", cascade="all, delete", lazy="selectin")

    reports = relationship("ProductReport", back_populates="product", cascade="all, delete-orphan")
    def __repr__(self):
        return f"<Product {self.name} (${self.price}) - Seller ID: {self.seller_id}>"
    
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published')", name="check_product_status"),
    )
    

class Category(Base):
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    parent_category_id = Column(Integer, ForeignKey("categories.category_id", ondelete="SET NULL"), nullable=True)


    parent_category = relationship("Category", remote_side=[category_id], backref="subcategories")


    product = relationship("Product", back_populates="category")

    def __repr__(self):
        return f"<Category {self.name}>"
    

class Order(Base):
    __tablename__ = "orders"

    order_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    
    order_status = Column(String(20), nullable=False, default="pending")
    order_payment_status = Column(String(20), nullable=False, default="pending")

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    coupon_id = Column(Integer, ForeignKey("coupons.coupon_id"), nullable=True)
    

    user = relationship("User", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payment = relationship("Payment", back_populates="order", uselist=False, cascade="all, delete-orphan")
    shipping = relationship("Shipping", back_populates="order", uselist=False, cascade="all, delete-orphan")
    coupon = relationship("Coupon", back_populates="orders")
    __table_args__ = (
        CheckConstraint("order_status IN ('pending', 'shipped', 'delivered', 'cancelled', 'returned')", name="check_order_status"),
        CheckConstraint("order_payment_status IN ('pending', 'completed', 'failed')", name="check_order_payment_status"),
    )


    def __repr__(self):
        return f"<Order {self.order_id} - {self.order_status} (${self.total_amount})>"


class OrderItem(Base):
    __tablename__ = "order_items"

    order_item_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    total_price = Column(DECIMAL(10, 2), nullable=False)

    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem {self.quantity} x Product {self.product_id} (Order {self.order_id})>"
    

class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)

    payment_method = Column(String(20), nullable=False)
    payment_status = Column(String(20), nullable=False, default="pending")

    transaction_id = Column(String(255), unique=True, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="payment")
    user = relationship("User", back_populates="payments")
    __table_args__ = (
        CheckConstraint("payment_method IN ('credit_card', 'paypal', 'bank_transfer', 'crypto')", name="check_payment_method"),
        CheckConstraint("payment_status IN ('pending', 'completed', 'failed')", name="check_payment_status"),
    )

    def __repr__(self):
        return f"<Payment {self.payment_id} - {self.payment_status} (${self.amount})>"
    

class Shipping(Base):
    __tablename__ = "shipping"

    shipping_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False)
    tracking_number = Column(String(100), unique=True, nullable=True)
    carrier = Column(String(100), nullable=True)
    estimated_delivery_date = Column(Date, nullable=True)

    shipping_status = Column(String(20), nullable=False, default="pending")
    created_at = Column(TIMESTAMP, server_default=func.now())

    
    order = relationship("Order", back_populates="shipping")
    
    __table_args__ = (
        CheckConstraint("shipping_status IN ('pending', 'shipped', 'delivered', 'returned')", name="check_shipping_status"),
    )
    
    def __repr__(self):
        return f"<Shipping {self.shipping_id} - {self.shipping_status} (Tracking: {self.tracking_number})>"


class Review(Base):
    __tablename__ = "reviews"

    review_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="rating_check"),)

    user = relationship("User", back_populates="reviews")
    product = relationship("Product", back_populates="reviews")

    def __repr__(self):
        return f"<Review {self.review_id} - {self.rating} stars>"


class Wishlist(Base):
    __tablename__ = "wishlists"

    wishlist_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="wishlists")
    product = relationship("Product", back_populates="wishlists")

    def __repr__(self):
        return f"<Wishlist {self.wishlist_id}>"


class Coupon(Base):
    __tablename__ = "coupons"

    coupon_id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    discount_percentage = Column(DECIMAL(5, 2), nullable=False)
    valid_from = Column(Date, nullable=True)
    valid_to = Column(Date, nullable=True)
    min_order_value = Column(DECIMAL(10, 2), default=0)
    max_discount_value = Column(DECIMAL(10, 2), nullable=True)
    coupon_status = Column(String(20), nullable=False, default="active")
    
    
    orders = relationship("Order", back_populates="coupon")

    # Constraints
    __table_args__ = (
        CheckConstraint("discount_percentage BETWEEN 0 AND 100", name="discount_percentage_check"),
        CheckConstraint("coupon_status IN ('active', 'expired', 'disabled')", name="check_coupon_status"),
    )

    def __repr__(self):
        return f"<Coupon {self.code} - {self.discount_percentage}%>"


class Cart(Base):
    __tablename__ = "cart"

    cart_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False)
    added_at = Column(TIMESTAMP, server_default=func.now())

    
    __table_args__ = (
        CheckConstraint("quantity BETWEEN 1 AND 50", name="quantity_check"),
    )

    
    user = relationship("User", back_populates="cart")
    product = relationship("Product", back_populates="cart")

    def __repr__(self):
        return f"<Cart {self.cart_id} - User {self.user_id} - Product {self.product_id}>"


class ProductReport(Base):
    __tablename__ = "product_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    reason = Column(Text, nullable=False)
    reported_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    product = relationship("Product", back_populates="reports")
    reported_by = relationship("User", foreign_keys=[user_id], back_populates="reports_made")
    reported_seller = relationship("User", foreign_keys=[seller_id], back_populates="reports_received")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    token = Column(String, primary_key=True, index=True)
    email = Column(String, index=True)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class VerificationToken(Base):
    __tablename__ = 'verification_tokens'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    
    token = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="verification_tokens")


class ProductImages(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.product_id'), nullable=False)
    image_url = Column(String(255), nullable=False)
    rank = Column(Float, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    product = relationship('Product', back_populates="product_images")


class Currency(Base):
    __tablename__ = 'currencies'

    code = Column(String(3), primary_key=True)
    name = Column(String(50), nullable=False)
    symbol = Column(String(5), nullable=True)

    products = relationship('Product', back_populates='currency')


class Otp(Base):
    __tablename__ = 'otp_s'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    
    otp = Column(Integer, index=True, nullable=False)
    phone = Column(String, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="otps")

