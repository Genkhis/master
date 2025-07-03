# models.py
from uuid import uuid4

from sqlalchemy import (
    Column, Integer, String, Float, Date, ForeignKey,
    Table, Boolean
)
from sqlalchemy.orm import relationship

from sqlalchemy.dialects.postgresql import UUID          # native Postgres uuid
from database import Base                                # your SQLAlchemy base


# ────────────────────────────────────────────────────────────
# Supplier (master)
# ────────────────────────────────────────────────────────────
class Supplier(Base):
    __tablename__ = "suppliers"

    supplier_id     = Column(Integer, primary_key=True, index=True)
    supplier_number = Column(String, unique=True, index=True)
    name            = Column(String, index=True)
    address         = Column(String)
    email           = Column(String)

    articles = relationship("Article", back_populates="supplier")


# ────────────────────────────────────────────────────────────
# Article (master)
# ────────────────────────────────────────────────────────────
class Article(Base):
    __tablename__ = "articles"

    article_id      = Column(Integer, primary_key=True)
    article_number  = Column(String, index=True)
    supplier_number = Column(String, ForeignKey("suppliers.supplier_number"))

    article_name    = Column(String)
    description     = Column(String)
    cost_type       = Column(String)
    category        = Column(String)
    dimension       = Column(String)
    item_no_ext     = Column(String)
    order_number    = Column(String)

    certification         = Column(String(10), default="-", nullable=False)  # LEED|…

    sale_unit             = Column(String)
    units_per_sale_unit   = Column(Float)
    unit_per_package      = Column(Integer, default=1)

    price_records = relationship("ArticlePrice", back_populates="article")
    supplier      = relationship("Supplier",      back_populates="articles")


# ────────────────────────────────────────────────────────────
# Association table: users ↔ roles (many-to-many)
# ────────────────────────────────────────────────────────────
roles_users = Table(
    "roles_users",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
)


# ────────────────────────────────────────────────────────────
# Role model
# ────────────────────────────────────────────────────────────
class Role(Base):
    __tablename__ = "roles"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name        = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)


# ────────────────────────────────────────────────────────────
# User model (compatible with FastAPI-Users v12 “sqlalchemy2” extra)
# ────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email          = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    is_active     = Column(Boolean, default=True, nullable=False)
    is_superuser  = Column(Boolean, default=False, nullable=False)
    is_verified   = Column(Boolean, default=False, nullable=False)

    roles = relationship("Role", secondary=roles_users, backref="users")


# ────────────────────────────────────────────────────────────
# ArticlePrice (transaction / history)
# ────────────────────────────────────────────────────────────
class ArticlePrice(Base):
    __tablename__ = "article_prices"

    price_id             = Column(Integer, primary_key=True)
    article_id           = Column(Integer, ForeignKey("articles.article_id"))

    purchase_date        = Column(Date)
    order_number         = Column(String)

    sale_unit            = Column(String)
    units_per_sale_unit  = Column(Float)
    sale_unit_price_eur  = Column(Float)
    unit_price_eur       = Column(Float)
    quantity             = Column(Float)
    amount               = Column(Float)

    delivery             = Column(Date)
    costplace            = Column(String)

    article = relationship("Article", back_populates="price_records")
