# models.py

from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

# ───────────────────────────────────────────────
# Supplier (master)
# ───────────────────────────────────────────────
class Supplier(Base):
    __tablename__ = "suppliers"

    supplier_id     = Column(Integer, primary_key=True, index=True)
    supplier_number = Column(String, unique=True, index=True)
    name            = Column(String, index=True)
    address         = Column(String)
    email           = Column(String)

    articles = relationship("Article", back_populates="supplier")


# ───────────────────────────────────────────────
# Article (master)
# ───────────────────────────────────────────────
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

    # NEW: sustainability label  (LEED | BREEAM | EUTax | DGNB | "-")
    certification         = Column(String(10), default="-", nullable=False)

    sale_unit             = Column(String)
    units_per_sale_unit   = Column(Float)
    unit_per_package      = Column(Integer, default=1)

    # relationships
    price_records = relationship("ArticlePrice", back_populates="article")
    supplier      = relationship("Supplier",   back_populates="articles")


# ───────────────────────────────────────────────
# ArticlePrice (transaction / history)
# ───────────────────────────────────────────────
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
