from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import create_engine, or_, func, text
from sqlalchemy.orm import sessionmaker, Session, joinedload
from models import Article, Supplier, ArticlePrice, User, Role
from pydantic import BaseModel, Field     
from datetime import date
import os
from fastapi_users import FastAPIUsers
from db_adapter import get_user_db
import pandas as pd
from managers import get_user_manager
from uuid import UUID
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy, CookieTransport
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from pathlib import Path
if Path(".env").exists():
    from dotenv import load_dotenv
    load_dotenv(override=True)

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")   # always a str fallback
import statistics
from database import Base, engine, SessionLocal, get_db
import os
from schemas import UserCreate, UserRead, UserUpdate
from io import BytesIO   
from typing import Optional, List
from fastapi.middleware.cors import CORSMiddleware
import logging
from passlib.context import CryptContext
from fastapi import Depends,APIRouter, Response, status
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Header, Depends

from schemas import UserCreate, UserRead, UserUpdate


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

jwt_strategy = JWTStrategy(
    secret=JWT_SECRET,          # ← use the same str for every component
    lifetime_seconds=3600,
)

cookie_transport = CookieTransport(
    cookie_name="jwt",
    cookie_max_age=3600,
    cookie_path="/",
    cookie_domain=".onrender.com",   
    cookie_secure=True,
    cookie_samesite="lax",
)
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=lambda: jwt_strategy,

)

fastapi_users = FastAPIUsers[User, UUID](
    get_user_manager,
    [auth_backend],
)

app = FastAPI()
@app.on_event("startup")
def on_startup():
    # create tables + seed roles & superuser
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for role_name in ("admin", "user"):
            if not db.query(Role).filter_by(name=role_name).first():
                db.add(Role(name=role_name))
        db.commit()

        admin_email = "admin@example.com"
        admin_pw    = "ChangeMe123!"
        if not db.query(User).filter_by(email=admin_email).first():
            hashed = get_password_hash(admin_pw)
            user = User(
                email=admin_email,
                hashed_password=hashed,
                is_active=True,
                is_superuser=True
            )
            admin_role = db.query(Role).filter_by(name="admin").one()
            user.roles.append(admin_role)
            db.add(user)
            db.commit()
    finally:
        db.close()

# 4) Include the routers, now passing your schemas here
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


# Enable CORS for requests coming from your Flask frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://procurement-ui.onrender.com",   #  ← add this
        "http://localhost:5000",                 #  dev
        # any other origins you need…
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        ogout_router = APIRouter(tags=["auth"])



logout_router = APIRouter(tags=["auth"])

app.include_router(logout_router)
@logout_router.post("/auth/logout", status_code=status.HTTP_200_OK)
def cookie_logout(response: Response):
    """
    Log the user out by clearing the JWT cookie.
    """
    response.delete_cookie(
        key="jwt",
        domain=".onrender.com",   # match whatever you set in CookieTransport
        path="/",
    )
    return {"detail": "Logged out"}


# Supplier models
class SupplierCreate(BaseModel):
    supplier_number: str
    name: str
    address: Optional[str] = None
    email: Optional[str] = None

class SupplierUpdate(BaseModel):
    supplier_number: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None

class SupplierOut(BaseModel):
    supplier_number: str
    name: str
    address: Optional[str] = None
    email: Optional[str] = None

    class Config:
        orm_mode = True

@app.get("/wake_db", tags=["Meta"])
def wake_db(db: Session = Depends(get_db)):
    """Ping the DB so Neon’s sleeping instance wakes up."""
    db.execute(text("SELECT 1"))
    return {"status": "awake"}

# Article models
class ArticleCreate(BaseModel):
    article_number: str
    article_name: str
    description: str
    cost_type: str
    category: str
    unit_per_package: int                    
    dimension: Optional[str] = None
    item_no_ext: str
    order_number: Optional[str] = None
    item_units: str
    certification: Optional[str] = "-"           # "LEED", "BREEAM" or "-"
    unit_per_package: Optional[int] = None   
    quantity: float
    unit_of_measure: str
    unit_price: float
    price_per_unit_of_measure: float
    amount: float
    delivery: Optional[date] = None
    supplier_number: Optional[str] = None
    costplace: Optional[str] = None  

class ArticleUpdate(BaseModel):
    article_number: Optional[int] = None
    article_name: Optional[str] = None
    description: Optional[str] = None
    cost_type: Optional[str] = None
    category: Optional[str] = None
    certification: Optional[str] = None          # keep None → unchanged
    dimension: Optional[str] = None
    item_no_ext: Optional[str] = None
    order_number: Optional[str] = None
    item_units: Optional[str] = None
    quantity: Optional[float] = None
    unit_of_measure: Optional[str] = None
    unit_price: Optional[float] = None
    price_per_unit_of_measure: Optional[float] = None
    amount: Optional[float] = None
    delivery: Optional[date] = None
    supplier_number: Optional[int] = None



# -------------------------------
# Schema Recreation (Development Only)
# -------------------------------


def create_price_record(
        *, db: Session,
        article_id: int,
        sale_unit: str,
        units_per_sale_unit: float,
        sale_unit_price_eur: float,
        unit_price_eur: float | None,
        quantity: float,
        order_number: str | None,
        delivery: date | None,
        costplace: str | None):

    # derive missing unit-price from sale-unit price
    if not unit_price_eur or unit_price_eur == 0:
        unit_price_eur = (
            sale_unit_price_eur / units_per_sale_unit
            if units_per_sale_unit else sale_unit_price_eur
        )

    db.add(ArticlePrice(
        article_id           = article_id,
        purchase_date        = date.today(),
        order_number         = order_number,
        sale_unit            = sale_unit,
        units_per_sale_unit  = units_per_sale_unit,
        sale_unit_price_eur  = sale_unit_price_eur,
        unit_price_eur       = unit_price_eur,
        quantity             = quantity,
        amount               = round(unit_price_eur * quantity, 2),
        delivery             = delivery,
        costplace            = costplace))
    db.commit()




# ─────────── backend_fastapi.py – replace the whole add_article() endpoint ────────────

ALLOWED_CERTS = {'-','LEED','EUTax','DGNB'}

@app.post("/add_article", tags=["Articles"])
def add_article(payload: ArticleCreate, db: Session = Depends(get_db)):

    # 0) validate certification string
    cert = (payload.certification or "-").strip().upper()
    if cert not in ALLOWED_CERTS:
        raise HTTPException(
            status_code=400,
            detail=f"certification must be one of {', '.join(ALLOWED_CERTS)}"
        )

    # 1) look for an existing master record
    art = (db.query(Article)
             .filter_by(article_number=payload.article_number,
                        supplier_number=payload.supplier_number)
             .first())

    # ───────────────────────────────────────── existing article ────────────────────
    if art:
        # optional: update the stored certification label
        if art.certification != cert:
            art.certification = cert
            db.commit()

        # only add a price-history row
        create_price_record(
            db                  = db,
            article_id          = art.article_id,
            sale_unit           = payload.sale_unit,
            units_per_sale_unit = payload.units_per_sale_unit,
            sale_unit_price_eur = payload.sale_unit_price_eur,
            unit_price_eur      = payload.unit_price_eur,
            quantity            = payload.quantity,
            order_number        = payload.order_number,
            delivery            = payload.delivery,
            costplace           = payload.costplace,
        )
        return {"message": "price update added", "article_id": art.article_id}

    # ───────────────────────────────────────── new master record ────────────────────
    if payload.supplier_number and not db.query(Supplier)\
                                         .filter_by(supplier_number=payload.supplier_number)\
                                         .first():
        raise HTTPException(400, "invalid supplier_number")

    art = Article(
        article_number       = payload.article_number,
        supplier_number      = payload.supplier_number,
        article_name         = payload.article_name,
        description          = payload.description,
        cost_type            = payload.cost_type,
        category             = payload.category,
        dimension            = payload.dimension,
        item_no_ext          = payload.item_no_ext,
        order_number         = payload.order_number,
        sale_unit            = payload.sale_unit,
        units_per_sale_unit  = payload.units_per_sale_unit,
        unit_per_package     = int(payload.unit_per_package or 1),
        certification        = cert,                               # ← NEW
    )
    db.add(art); db.commit(); db.refresh(art)

    create_price_record(
        db                  = db,
        article_id          = art.article_id,
        sale_unit           = payload.sale_unit,
        units_per_sale_unit = payload.units_per_sale_unit,
        sale_unit_price_eur = payload.sale_unit_price_eur,
        unit_price_eur      = payload.unit_price_eur,
        quantity            = payload.quantity,
        order_number        = payload.order_number,
        delivery            = payload.delivery,
        costplace           = payload.costplace,
    )

    return {"message": "article added successfully", "article_id": art.article_id}



# Get Article Endpoint
@app.get("/get_article/{article_id}", tags=["Articles"])
def get_article(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.article_id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return {
        "article_id": article.article_id,
        "article_number": article.article_number,
        "article_name": article.article_name,
        "description": article.description,
        "cost_type": article.cost_type,
        "category": article.category,
        "dimension": article.dimension,
        "item_no_ext": article.item_no_ext,
        "order_number": article.order_number,
        "item_units": article.item_units,
        "quantity": article.quantity,
        "unit_of_measure": article.unit_of_measure,
        "unit_price": article.unit_price,
        "price_per_unit_of_measure": article.price_per_unit_of_measure,
        "amount": article.amount,
        "delivery": article.delivery,
        "supplier_number": article.supplier_number
    }

# Update Article (Full)
@app.put("/update_article/{article_id}", tags=["Articles"])
def update_article(article_id: int, article_data: ArticleCreate, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.article_id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    for key, value in article_data.dict().items():
        setattr(article, key, value)
    db.commit()
    return {"message": "Article updated successfully"}

@app.patch("/update_article_partial/{article_id}", tags=["Articles"])
def update_article_partial(article_id: int,
                           article_data: ArticleUpdate,
                           db: Session = Depends(get_db)):
    art = db.query(Article).filter_by(article_id=article_id).first()
    if not art:
        raise HTTPException(404, "Article not found")

    incoming = article_data.dict(exclude_unset=True)
    for k, v in incoming.items():
        setattr(art, k, v)

    # ── recompute dependent values when relevant inputs changed ────
    if {"unit_price", "unit_per_package"} & incoming.keys():
        art.price_per_unit_of_measure = round(
            art.unit_price / (art.unit_per_package or 1), 4
        )
    if {"unit_price", "quantity"} & incoming.keys():
        art.amount = art.quantity * art.unit_price

    db.commit()
    return {"message": "Article partially updated successfully"}

# Delete Article
@app.delete("/delete_article/{article_id}", tags=["Articles"])
def delete_article(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.article_id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    db.delete(article)
    db.commit()
    return {"message": "Article deleted successfully"}

# FastAPI: backend_fastapi.py

# ─────────────────────────────────────────────────────────────────────
# /articles   –  einen kompakten Datensatz pro Artikel liefern
# ─────────────────────────────────────────────────────────────────────
@app.get("/articles", tags=["Articles"])
def list_articles(
    query: str = Query("", description="Search term"),
    filter_by: str = Query("", description="Field to filter on"),
    db: Session = Depends(get_db)
):
    query = query.strip()
    filter_by = filter_by.strip()
    valid_fields = {
        "article_number", "article_name", "description", "item_no_ext",
        "cost_type", "category", "supplier_number", "certification"  

    }

    # 1) Basissuche aufbauen
    if query:
        if filter_by == "supplier_name":
            q = (db.query(Article)
                    .join(Article.supplier)
                    .options(joinedload(Article.supplier))
                    .filter(func.lower(Supplier.name)
                            .ilike(f"%{query.lower()}%")))
        elif filter_by in valid_fields:
            q = (db.query(Article)
                    .options(joinedload(Article.supplier))
                    .filter(func.lower(func.trim(getattr(Article, filter_by)))
                            .ilike(f"%{query.lower()}%")))
        else:
            q = (db.query(Article)
                    .options(joinedload(Article.supplier))
                    .filter(or_(
                        Article.article_number.ilike(f"%{query}%"),
                        Article.article_name.ilike(f"%{query}%"),
                        Article.description.ilike(f"%{query}%"),
                        Article.item_no_ext.ilike(f"%{query}%"),
                        Article.cost_type.ilike(f"%{query}%"),
                        Article.category.ilike(f"%{query}%"),
                        Article.supplier_number.ilike(f"%{query}%"),
                        Article.certification.ilike(f"%{query}%")
                    )))
        articles = q.all()
    else:
        articles = db.query(Article).options(joinedload(Article.supplier)).all()

    # 2) je Artikel eine aggregierte Zeile bauen
    result = []
    for art in articles:
        unit_prices = [r.unit_price_eur for r in art.price_records if r.unit_price_eur]
        sale_prices = [r.sale_unit_price_eur for r in art.price_records if r.sale_unit_price_eur]

        result.append({
            "article_id"          : art.article_id,
            "article_number"      : art.article_number,
            "article_name"        : art.article_name,
            "description"         : art.description,
            "cost_type"           : art.cost_type,
            "category"            : art.category,
            "dimension"           : art.dimension,
            "item_no_ext"         : art.item_no_ext,
            "sale_unit"           : next((r.sale_unit for r in art.price_records if r.sale_unit), None),
            "units_per_sale_unit" : next((r.units_per_sale_unit for r in art.price_records if r.units_per_sale_unit), None),
            "low_sale_price"      : min(sale_prices) if sale_prices else None,
            "high_sale_price"     : max(sale_prices) if sale_prices else None,
            "avg_sale_price"      : round(sum(sale_prices)/len(sale_prices), 2) if sale_prices else None,
            "low_unit_price"      : min(unit_prices) if unit_prices else None,
            "high_unit_price"     : max(unit_prices) if unit_prices else None,
            "avg_unit_price"      : round(sum(unit_prices)/len(unit_prices), 4) if unit_prices else None,
            "supplier_number"     : art.supplier_number,
            "supplier_name"       : art.supplier.name if art.supplier else None,
            "certification"       : art.certification        
        })

    return result


class SearchClause(BaseModel):
    query: str = Field(..., min_length=1)
    field: str

MULTI_FIELDS = {
    "article_number", "article_name", "description", "item_no_ext",
    "cost_type", "category", "supplier_number", "supplier_name",
    "certification"
}

def _aggregate(articles: list[Article]) -> list[dict]:
    """Factorised step-2 logic (was duplicated)."""
    rows = []
    for art in articles:
        unit_prices = [r.unit_price_eur for r in art.price_records if r.unit_price_eur]
        sale_prices = [r.sale_unit_price_eur for r in art.price_records if r.sale_unit_price_eur]

        rows.append({
            "article_id"         : art.article_id,
            "article_number"     : art.article_number,
            "article_name"       : art.article_name,
            "description"        : art.description,
            "cost_type"          : art.cost_type,
            "category"           : art.category,
            "dimension"          : art.dimension,
            "item_no_ext"        : art.item_no_ext,
            "sale_unit"          : next((r.sale_unit for r in art.price_records if r.sale_unit), None),
            "units_per_sale_unit": next((r.units_per_sale_unit for r in art.price_records if r.units_per_sale_unit), None),
            "low_sale_price"     : min(sale_prices) if sale_prices else None,
            "high_sale_price"    : max(sale_prices) if sale_prices else None,
            "avg_sale_price"     : round(sum(sale_prices)/len(sale_prices), 2) if sale_prices else None,
            "low_unit_price"     : min(unit_prices) if (unit_prices := [r.unit_price_eur for r in art.price_records if r.unit_price_eur]) else None,
            "high_unit_price"    : max(unit_prices) if unit_prices else None,
            "avg_unit_price"     : round(sum(unit_prices)/len(unit_prices), 4) if unit_prices else None,
            "supplier_number"    : art.supplier_number,
            "supplier_name"      : art.supplier.name if art.supplier else None,
            "certification"      : art.certification,
        })
    return rows


@app.post("/articles/advanced", tags=["Articles"])
def advanced_articles(
    clauses: list[SearchClause],
    db: Session = Depends(get_db)
):
    """
    Expects JSON list like
       [{"query":"screw","field":"article_name"},
        {"query":"acme","field":"supplier_name"}]
    Returns the intersection of all clauses.
    """
    if not clauses:
        return _aggregate(
            db.query(Article).options(joinedload(Article.supplier)).all()
        )

    q = db.query(Article).options(joinedload(Article.supplier))

    for clause in clauses:
        term  = clause.query.strip().lower()
        field = clause.field.strip()

        if field not in MULTI_FIELDS:
            raise HTTPException(400, f"Unknown field '{field}'")

        if field == "supplier_name":
            q = q.filter(func.lower(Supplier.name).ilike(f"%{term}%"))
        else:
            col = getattr(Article, field)
            q = q.filter(func.lower(func.trim(col)).ilike(f"%{term}%"))

    return _aggregate(q.all())


@app.get("/supplier_articles/{supplier_number}", tags=["Suppliers"])
def supplier_articles(supplier_number: str, db: Session = Depends(get_db)):
    norm = supplier_number.strip().lower()
    articles = (
        db.query(Article)
          .options(joinedload(Article.price_records))
          .filter(func.lower(func.trim(Article.supplier_number)) == norm)
          .all()
    )
    if not articles:
        raise HTTPException(
            status_code=404,
            detail=f"No articles found for supplier {supplier_number}"
        )

    results = []
    for art in articles:
        # collect all unit-prices
        prices = [r.unit_price_eur for r in art.price_records if r.unit_price_eur is not None]
        if prices:
            low    = min(prices)
            high   = max(prices)
            median = statistics.median(prices) if len(prices) > 1 else "N/A"
        else:
            low = high = median = "N/A"

        # pick the most recent price record
        latest = max(
            art.price_records,
            key=lambda r: r.purchase_date or date.min,
            default=None
        )

        results.append({
            "article_id"          : art.article_id,
            "article_number"      : art.article_number,
            "article_name"        : art.article_name,
            "description"         : art.description,
            "cost_type"           : art.cost_type,
            "category"            : art.category,
            "dimension"           : art.dimension,
            "item_no_ext"         : art.item_no_ext,
            "order_number"        : art.order_number,
            "sale_unit"           : art.sale_unit,
            "units_per_sale_unit" : art.units_per_sale_unit,
            "unit_price_eur"      : latest.unit_price_eur if latest else None,
            "low_price"           : low,
            "high_price"          : high,
            "median_price"        : median,
            "delivery"            : latest.delivery if latest else None,
            "costplace"           : latest.costplace if latest else None,
            "supplier_number"     : art.supplier_number,
            "supplier_name"       : art.supplier.name if art.supplier else None,
        })

    return results



# ───────────────────────────────────────────────────────────────────────────
# GET /price_history_by_composite/{supplier_number}/{item_no_ext}
# ───────────────────────────────────────────────────────────────────────────
@app.get("/price_history_by_composite/{supplier_number}/{item_no_ext}",
         tags=["Articles"])
def price_history_by_composite(supplier_number: str,
                               item_no_ext: str,
                               db: Session = Depends(get_db)):

    sup_key  = supplier_number.strip().lower()
    item_key = item_no_ext.strip().lower()

    art = (db.query(Article)
             .options(joinedload(Article.price_records))
             .filter(func.lower(func.trim(Article.supplier_number)) == sup_key,
                     func.lower(func.trim(Article.item_no_ext))     == item_key)
             .first())

    if not art:
        raise HTTPException(404, "No article found for the given composite key")

    # build history rows – every row has price_per_unit_of_measure!
    rows = []
    for rec in sorted(art.price_records,
                      key=lambda r: r.purchase_date or date.min):
        ppu = rec.unit_price_eur / (rec.units_per_sale_unit or 1)
        rows.append({
            "price_id": rec.price_id,
            "purchase_date": rec.purchase_date,
            "order_number": rec.order_number,
            "sale_unit": rec.sale_unit,
            "units_per_sale_unit": rec.units_per_sale_unit,
            "quantity": rec.quantity,
            "unit_price_eur": rec.unit_price_eur,
            "sale_unit_price_eur": rec.sale_unit_price_eur,
            "price_per_unit_of_measure": round(ppu, 4),
            "amount": rec.amount,
            "delivery": rec.delivery,
            "costplace": rec.costplace
        })

    # aggregated statistics
    prices = [r["unit_price_eur"] for r in rows]
    ppu_list = [r["price_per_unit_of_measure"] for r in rows]

    stats = {
        "low_price": min(prices) if prices else None,
        "high_price": max(prices) if prices else None,
        "avg_price": round(sum(prices) / len(prices), 2) if prices else None,
        "low_ppu": min(ppu_list) if ppu_list else None,
        "high_ppu": max(ppu_list) if ppu_list else None,
        "avg_ppu": round(sum(ppu_list) / len(ppu_list), 4) if ppu_list else None
    }

    return {
        "article": {
            "article_id": art.article_id,
            "article_name": art.article_name,
            "item_no_ext": art.item_no_ext,
            "description": art.description,
            "dimension": art.dimension or "N/A",
            "sale_unit": art.sale_unit,
            "units_per_sale_unit": art.units_per_sale_unit,
            "supplier_number": art.supplier_number,
            "supplier_name": art.supplier.name if art.supplier else None,
        },
        "stats": stats,
        "price_history": rows
    }



# Get Article by Composite Key

@app.get("/article_by_supplier_item/{supplier_number}/{item_no_ext}", tags=["Articles"])
def get_article_by_supplier_item(supplier_number: str, item_no_ext: str, db: Session = Depends(get_db)):
    article = db.query(Article).options(joinedload(Article.supplier)).filter(
        Article.supplier_number == supplier_number,
        Article.item_no_ext == item_no_ext
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return {
        "article_id": article.article_id,
        "article_number": article.article_number,
        "article_name": article.article_name,
        "description": article.description,
        "cost_type": article.cost_type,
        "category": article.category,
        "dimension": article.dimension,
        "item_no_ext": article.item_no_ext,
        "order_number": article.order_number,
        "item_units": article.item_units,
        "quantity": article.quantity,
        "unit_of_measure": article.unit_of_measure,
        "unit_price": article.unit_price,
        "price_per_unit_of_measure": article.price_per_unit_of_measure,
        "amount": article.amount,
        "delivery": article.delivery.isoformat() if article.delivery else None,
        "supplier_number": article.supplier_number,
        "supplier_name": article.supplier.name if article.supplier else None
    }

REQUIRED_COLUMNS: set[str] = {
    "article_number", "article_name", "description",
    "cost_type", "category", "dimension",
    "item_no_ext", "order_number",
    "sale_unit", "units_per_sale_unit",
    "sale_unit_price_eur", "unit_price_eur",
    "quantity", "amount", "delivery",
    "unit_per_package",          
    "supplier_number", "costplace"
}


ALLOWED_CERTS = {"LEED", "BREEAM", "-"}

# add "certification" to the *optional* header set
REQUIRED_COLUMNS: set[str] = {
    "article_number", "article_name", "description",
    "cost_type", "category", "dimension",
    "item_no_ext", "order_number",
    "sale_unit", "units_per_sale_unit",
    "sale_unit_price_eur", "unit_price_eur",
    "quantity", "amount", "delivery",
    "unit_per_package",
    "supplier_number", "costplace",
    # "certification" intentionally *not* required
}

@app.post("/upload_articles", tags=["Articles"])
async def upload_articles(
    file: UploadFile = File(...),
    db:   Session    = Depends(get_db)
):
    # 0) read + normalise headers
    df = pd.read_excel(BytesIO(await file.read()), engine="openpyxl")
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.fillna("")

    # 1) header validation
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Pflichtspalte(n) fehlen: {', '.join(sorted(missing))}"
        )

    # 2) type conversions
    num_cols = [
        "units_per_sale_unit", "sale_unit_price_eur", "unit_price_eur",
        "quantity", "amount", "unit_per_package"
    ]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["delivery"] = pd.to_datetime(df["delivery"], errors="coerce")

    inserted_ids: list[int]  = []
    missing_suppliers: set[str] = set()
    cert_errors: list[str]   = []

    # 3) iterate rows
    for _, row in df.iterrows():
        art_no   = row["article_number"]
        supp_no  = str(row["supplier_number"]).strip() or None
        cert_raw = str(row.get("certification", "-")).strip().upper() or "-"
        if cert_raw not in ALLOWED_CERTS:
            cert_errors.append(f"{art_no}/{supp_no or 'n/a'} -> {cert_raw}")
            continue                                   # skip invalid rows

        # unknown supplier → collect & skip
        if supp_no and not db.query(Supplier).filter_by(supplier_number=supp_no).first():
            missing_suppliers.add(supp_no)
            continue

        art = (db.query(Article)
                 .filter_by(article_number=art_no, supplier_number=supp_no)
                 .first())

        # ─────────── create master if absent ───────────
        if not art:
            art = Article(
                article_number       = art_no,
                supplier_number      = supp_no,
                article_name         = row["article_name"],
                description          = row["description"],
                cost_type            = row["cost_type"],
                category             = row["category"],
                dimension            = row["dimension"],
                item_no_ext          = row["item_no_ext"],
                order_number         = row["order_number"],
                sale_unit            = row["sale_unit"],
                units_per_sale_unit  = row["units_per_sale_unit"],
                unit_per_package     = int(row["unit_per_package"] or 1),
                certification        = cert_raw,       # ← NEW
            )
            db.add(art); db.commit(); db.refresh(art)

        # ─────────── otherwise update certification if changed ───────────
        elif art.certification != cert_raw:
            art.certification = cert_raw
            db.commit()

        # always add price row
        create_price_record(
            db                 = db,
            article_id         = art.article_id,
            sale_unit          = row["sale_unit"],
            units_per_sale_unit= float(row["units_per_sale_unit"] or 0),
            sale_unit_price_eur= float(row["sale_unit_price_eur"] or 0),
            unit_price_eur     = float(row["unit_price_eur"] or 0),
            quantity           = float(row["quantity"] or 0),
            order_number       = row["order_number"] or None,
            delivery           = row["delivery"]   or None,
            costplace          = (row["costplace"] if str(row["costplace"]).strip()
                                  else None),
        )
        inserted_ids.append(art.article_id)

    # 4) summary
    msg = f"processed {len(inserted_ids)} row(s)"
    if missing_suppliers:
        msg += f", skipped {len(missing_suppliers)} (unknown supplier)"
    if cert_errors:
        msg += f", skipped {len(cert_errors)} (invalid certification)"

    return {
        "message"          : msg,
        "article_ids"      : inserted_ids,
        "missing_suppliers": sorted(missing_suppliers),
        "cert_errors"      : cert_errors,
    }



# ------------------------------------------------------------------
#  /upload_suppliers  –  bulk upsert (insert + update) for suppliers
# ------------------------------------------------------------------
MANDATORY_SUPPLIER_COLUMNS = {"supplier_number", "name"}
OPTIONAL_SUPPLIER_COLUMNS  = {"address", "email"}

@app.post("/upload_suppliers", tags=["Suppliers"])
async def upload_suppliers(
    file: UploadFile = File(...),
    db:   Session    = Depends(get_db)
):
    # 0) read × normalise headers
    df = pd.read_excel(BytesIO(await file.read()), engine="openpyxl")
    df.columns = [c.strip().lower() for c in df.columns]
    df = (
        df.rename(columns={"supplier": "supplier_number"})  # accept “supplier” alias
          .fillna("")                                       # NA→""
    )

    # 1) header validation
    header  = set(df.columns)
    missing = MANDATORY_SUPPLIER_COLUMNS - header
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Pflichtspalte(n) fehlen: {', '.join(sorted(missing))}"
        )

    # 2) force key columns to string (protect against numeric XLSX cells)
    df["supplier_number"] = df["supplier_number"].astype(str).str.strip()

    upserted: list[str] = []

    # 3) iterate rows
    for _, row in df.iterrows():
        sup_no = row["supplier_number"]
        name   = str(row["name"]).strip()

        # skip if either mandatory field is blank
        if not sup_no or not name:
            continue

        # build payload only from allowed columns
        payload = {
            "name"   : name,
            "address": str(row.get("address", "")).strip() or None,
            "email"  : str(row.get("email", "")).strip()   or None,
        }

        sup = db.query(Supplier).filter_by(supplier_number=sup_no).first()

        if sup:                                           # update existing
            for k, v in payload.items():
                setattr(sup, k, v)
            action = "updated"
        else:                                             # insert new
            sup = Supplier(supplier_number=sup_no, **payload)
            db.add(sup)
            action = "inserted"

        db.commit()
        upserted.append(f"{sup_no}:{action}")

    return {
        "message"   : f"processed {len(upserted)} row(s)",
        "operations": upserted                             
    }




def serialize_articles(articles: list[Article]) -> list[dict]:
    rows = []
    for art in articles:
        unit_prices = [r.unit_price_eur for r in art.price_records if r.unit_price_eur]
        sale_prices = [r.sale_unit_price_eur for r in art.price_records if r.sale_unit_price_eur]

        rows.append({
            "article_id"         : art.article_id,
            "article_number"     : art.article_number,
            "article_name"       : art.article_name,
            "description"        : art.description,
            "cost_type"          : art.cost_type,
            "category"           : art.category,
            "dimension"          : art.dimension,
            "item_no_ext"        : art.item_no_ext,
            "sale_unit"          : next((r.sale_unit for r in art.price_records if r.sale_unit), None),
            "units_per_sale_unit": next((r.units_per_sale_unit for r in art.price_records if r.units_per_sale_unit), None),
            "low_sale_price"     : min(sale_prices) if sale_prices else None,
            "high_sale_price"    : max(sale_prices) if sale_prices else None,
            "avg_sale_price"     : round(sum(sale_prices)/len(sale_prices), 2) if sale_prices else None,
            "low_unit_price"     : min(unit_prices) if unit_prices else None,
            "high_unit_price"    : max(unit_prices) if unit_prices else None,
            "avg_unit_price"     : round(sum(unit_prices)/len(unit_prices), 4) if unit_prices else None,
            "supplier_number"    : art.supplier_number,
            "supplier_name"      : art.supplier.name if art.supplier else None,
            "certification"      : art.certification,
        })
    return rows

@app.post("/add_supplier", tags=["Suppliers"])
def add_supplier(supplier: SupplierCreate, db: Session = Depends(get_db)):
    new_supplier = Supplier(**supplier.dict())
    db.add(new_supplier)
    db.commit()
    db.refresh(new_supplier)
    return {"message": "Supplier added successfully", "supplier_number": new_supplier.supplier_number}

@app.get("/suppliers", tags=["Suppliers"], response_model=List[SupplierOut])
def list_suppliers(db: Session = Depends(get_db)):
    suppliers = db.query(Supplier).all()
    return suppliers

@app.get("/get_supplier/{supplier_number}", tags=["Suppliers"], response_model=SupplierOut)
def get_supplier(supplier_number: str, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.supplier_number == supplier_number).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@app.get("/health", tags=["Meta"])
def health():
    return {"status": "ok"}

@app.get("/article_suggestions", tags=["Articles"])
def article_suggestions(q: str = Query(..., min_length=3), db: Session = Depends(get_db)):
    # Query for articles that match the query in their name.
    suggestions = (db.query(Article.article_name)
                     .filter(Article.article_name.ilike(f"%{q}%"))
                     .limit(10)
                     .all())
    return [s[0] for s in suggestions]

if __name__ == "__main__":
    app.run(debug=True, port=8001)


    