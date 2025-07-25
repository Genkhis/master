﻿from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, make_response, abort
)
from flask import g       

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os, requests, jwt, datetime
from functools import wraps
import logging
from types import SimpleNamespace



# ───────────────────────────
# Flask setup
# ───────────────────────────
app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)
app.secret_key = os.getenv("FLASK_SECRET", "local-dev-secret")

# ───────────────────────────
# Config: DB + API URL
# ───────────────────────────
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "sqlite:///app.db"                    # local fallback
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db       = SQLAlchemy(app)
migrate  = Migrate(app, db)

BASE_API_URL = os.getenv("API_URL", "http://127.0.0.1:8001")
API_TIMEOUT  = 8          # seconds       ← NEW
app.config["API_URL"] = BASE_API_URL

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")   

# expose {{ API_URL }} in every template
@app.context_processor
def inject_api_url():
    return {"API_URL": app.config["API_URL"]}
@app.context_processor
def inject_login_state():
    return {"is_logged_in": _current_user()}

log = logging.getLogger("login-guard")
log.setLevel(logging.INFO)

# ───────────────────────────
# Auth helper & guard
# ───────────────────────────
EXEMPT_ENDPOINTS = {
    "login", "static", "favicon",        
}

@app.context_processor
def inject_flags():
    return dict(
        is_logged_in=bool(request.cookies.get("bearer")),
        is_superuser=is_super(),          # now defined above
    )


@app.before_request
def require_login_for_protected_pages():
    # 1.  Let public stuff pass through
    if request.endpoint in EXEMPT_ENDPOINTS:
        return                      # allowed

    # 2.  Logged-in?  → allow
    if _current_user():
        return

    # 3.  Otherwise bounce to /login, preserving target
    next_url = request.full_path.rstrip("?")  # keeps query string
    login_url = url_for("login", next=next_url, _external=False)
    return redirect(login_url)
def is_super() -> bool:
    """
    Return True when the logged-in user is a superuser.
    FastAPI-Users doesn't embed that flag in the JWT, so we fetch
    it once via /users/me and cache it in Flask's `g` object.
    """
    if hasattr(g, "_is_super"):
        return g._is_super

    token = request.cookies.get("bearer")
    if not token:
        g._is_super = False
        return False

    try:
        r = requests.get(
            f"{BASE_API_URL}/users/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT,
        )
        g._is_super = r.ok and r.json().get("is_superuser", False)
    except requests.RequestException:
        g._is_super = False

    return g._is_super
def _current_user() -> bool:
    """Return True when a valid JWT is present in cookie or header."""
    token = (
        request.cookies.get("bearer") or
        request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    )
    if not token:
        return False

    try:
        # ignore the “aud” claim produced by FastAPI-Users
        jwt.decode(token, JWT_SECRET,
                   algorithms=["HS256"],
                   options={"verify_aud": False})
        return True
    except jwt.PyJWTError:
        return False




# ───────────────────────────
# Helper
# ───────────────────────────
def _extract_filter_lists(form):
    queries = [q.strip() for q in form.getlist("query[]") if q.strip()]
    fields  = form.getlist("filter_by[]")[: len(queries)]
    return queries, fields

# ───────────────────────────
# Routes
# ───────────────────────────
@app.route("/login", methods=["GET"])
def login():
    """Render login page; token handling done client-side JS."""
    return render_template("login.html")

# Home
@app.route("/", methods=["GET", "POST"])
def index():
    token = _token_from_browser()           # 🔸 NEW

    query     = request.args.get("query", "")
    filter_by = request.args.get("filter_by", "")
    if request.method == "POST":
        query     = request.form.get("query", "")
        filter_by = request.form.get("filter_by", "")

    resp = _api_get(f"/articles/?query={query}&filter_by={filter_by}",
                    token=token)            # 🔸 NEW

    articles = resp.json() if resp.ok else []
    if not resp.ok:
        flash("Error fetching articles", "danger")

    return render_template("index.html", articles=articles)


def _dummy_response(code: int, text: str):
    """Return an object that looks like a `requests.Response` but is static."""
    return SimpleNamespace(
        ok         = False,
        status_code= code,
        text       = text,
        json       = lambda: {},   # empty JSON payload
    )



@app.route("/all_articles", methods=["GET", "POST"])
def all_articles():
    # 0) pick up the JWT (None when the guard let an anonymous user through)
    token = _token_from_browser()

    if request.method == "POST":
        queries, fields = _extract_filter_lists(request.form)
    else:
        q = request.args.get("query", "").strip()
        f = request.args.get("filter_by", "")
        queries, fields = ([q] if q else []), ([f] if f else [])

    filter_pairs = list(zip(queries, fields))

    if not filter_pairs:                               
        resp = _api_get("/articles/", token=token)

    elif len(filter_pairs) == 1:                      
        q, f = filter_pairs[0]
        resp = _api_get(f"/articles/?query={q}&filter_by={f}", token=token)

    else:                                              
        payload = [{"query": q, "field": f} for q, f in filter_pairs]
        resp = _api_post("/articles/advanced", json=payload, token=token)

    articles = resp.json() if resp.ok else []
    if not resp.ok:
        flash("Error fetching articles", "danger")

    return render_template(
        "all-articles.html",
        articles=articles,
        filter_pairs=filter_pairs,
    )



def _token_from_browser() -> str | None:
    return request.cookies.get("bearer") 

def _api_get(path: str, *, token: str | None = None):
    hdrs = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        return requests.get(f"{BASE_API_URL}{path}",
                            headers=hdrs, timeout=API_TIMEOUT)
    except requests.Timeout:
        app.logger.warning("API timeout for %s", path)
        return _dummy_response(504, "Gateway Timeout")
    except requests.RequestException as exc:
        app.logger.error("API error for %s → %s", path, exc)
        return _dummy_response(502, "Bad Gateway")

def _api_post(path: str, *, json: dict | None = None, token: str | None = None):
    hdrs = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        return requests.post(f"{BASE_API_URL}{path}", json=json,
                             headers=hdrs, timeout=API_TIMEOUT)
    except requests.Timeout:
        return _dummy_response(504, "Gateway Timeout")
    except requests.RequestException:
        return _dummy_response(502, "Bad Gateway")



# ────────── Add Article
@app.route("/add_article", methods=["GET", "POST"])
def add_article():
    if request.method == "POST":
        supplier_number = request.form.get("supplier_number", "").strip() or None
        data = {
            "article_number": request.form["article_number"],
            "article_name"  : request.form["article_name"],
            "description"   : request.form["description"],
            "cost_type"     : request.form["cost_type"],
            "category"      : request.form["category"],
            "dimension"     : request.form.get("dimension", ""),
            "item_no_ext"   : request.form["item_no_ext"],
            "order_number"  : request.form.get("order_number", ""),
            "item_units"    : request.form["item_units"],
            "quantity"      : float(request.form["quantity"]),
            "unit_of_measure": request.form["unit_of_measure"],
            "unit_price"    : float(request.form["unit_price"]),
            "price_per_unit_of_measure": float(request.form["price_per_unit_of_measure"]),
            "amount"        : float(request.form["amount"]),
            "delivery"      : request.form.get("delivery") or None,
            "supplier_number": supplier_number,
            "costplace"     : request.form.get("costplace") or None,
        }
        resp = requests.post(f"{BASE_API_URL}/add_article", json=data)
        flash(
            "Article added successfully!" if resp.ok else "Error adding article",
            "success" if resp.ok else "danger"
        )
        return redirect(url_for("index"))

    return render_template("add_article.html")

# ────────── Edit Article
@app.route("/edit_article/<int:article_id>", methods=["GET", "POST"])
def edit_article(article_id):
    if request.method == "POST":
        supplier_number = request.form.get("supplier_number", "").strip() or None
        patch_data = {
            k: request.form.get(k) for k in [
                "article_number","article_name","description","cost_type","category",
                "dimension","item_no_ext","order_number","item_units","unit_of_measure",
                "certification"
            ]
        } | {
            "quantity" : float(request.form.get("quantity", 0) or 0),
            "unit_price": float(request.form.get("unit_price", 0) or 0),
            "price_per_unit_of_measure": float(request.form.get("price_per_unit_of_measure", 0) or 0),
            "amount": float(request.form.get("amount", 0) or 0),
            "delivery": request.form.get("delivery") or None,
            "supplier_number": supplier_number,
            "costplace": request.form.get("costplace") or None,
        }

        resp = requests.patch(
            f"{BASE_API_URL}/update_article_partial/{article_id}",
            json=patch_data
        )
        flash(
            "Article updated successfully!" if resp.ok
            else f"Error updating article – {resp.text}",
            "success" if resp.ok else "danger"
        )
        return redirect(url_for("index"))

    resp = requests.get(f"{BASE_API_URL}/get_article/{article_id}")
    if not resp.ok:
        flash("Error retrieving article.", "danger")
        return redirect(url_for("index"))

    return render_template("edit_article.html", article=resp.json())

# ────────── Delete Article
@app.route("/delete_article/<int:article_id>")
def delete_article(article_id):
    resp = requests.delete(f"{BASE_API_URL}/delete_article/{article_id}")
    flash(
        "Article deleted successfully!" if resp.ok
        else f"Error deleting article: {resp.status_code} - {resp.text}",
        "success" if resp.ok else "danger"
    )
    return redirect(url_for("index"))

# ------------------------------------------------------------------
# Price history
# ------------------------------------------------------------------
@app.route("/price_history/<supplier_number>/<item_no_ext>")
def price_history(supplier_number, item_no_ext):
    hist = requests.get(
        f"{BASE_API_URL}/price_history_by_composite/{supplier_number}/{item_no_ext}"
    )
    if not hist.ok:
        flash("Error fetching price history", "danger")
        return redirect(url_for("index"))

    supplier = requests.get(f"{BASE_API_URL}/get_supplier/{supplier_number}")
    supplier = supplier.json() if supplier.ok else None

    j = hist.json()
    return render_template(
        "price_history.html",
        article=j["article"],
        stats=j["stats"],
        history=j["price_history"],
        supplier=supplier
    )

# ------------------------------------------------------------------
# Supplier list
# ------------------------------------------------------------------
@app.route("/suppliers")
def suppliers():
    PAGE_SIZE = 40
    page  = max(1, int(request.args.get("page", 1)))
    query = request.args.get("query", "").strip().lower()

    resp = requests.get(f"{BASE_API_URL}/suppliers")
    if not resp.ok:
        flash("Error fetching suppliers", "danger")
        return render_template(
            "suppliers.html", suppliers=[], page=1, total_pages=1, query=query
        )

    suppliers = resp.json()
    suppliers.sort(key=lambda s: (s.get("name") or "").lower())

    if query:
        suppliers = [s for s in suppliers if query in (s.get("name") or "").lower()]

    total_pages = max(1, (len(suppliers) + PAGE_SIZE - 1) // PAGE_SIZE)
    suppliers   = suppliers[(page-1)*PAGE_SIZE : page*PAGE_SIZE]

    return render_template(
        "suppliers.html",
        suppliers=suppliers,
        page=page,
        total_pages=total_pages,
        query=query
    )

# ------------------------------------------------------------------
# Supplier > Articles page
# ------------------------------------------------------------------
@app.route("/supplier_articles/<supplier_number>")
def supplier_articles(supplier_number):
    supplier = requests.get(f"{BASE_API_URL}/get_supplier/{supplier_number}")
    supplier = supplier.json() if supplier.ok else None

    articles = requests.get(f"{BASE_API_URL}/supplier_articles/{supplier_number}")
    articles = articles.json() if articles.ok else []

    if not supplier:
        flash("Error fetching supplier details", "danger")
    if not articles:
        flash("Error fetching supplier articles", "danger")

    return render_template("supplier_articles.html",
                           supplier=supplier, articles=articles)

# ------------------------------------------------------------------
# Upload articles Excel
# ------------------------------------------------------------------
@app.route("/upload_excel", methods=["GET", "POST"])
def upload_excel():
    skipped_suppliers: list[str] = []
    upload_summary:   str | None = None          # „processed … row(s)“
    error_msg:        str | None = None

    if request.method == "POST":
        file_obj = request.files.get("file")

        if not file_obj or file_obj.filename == "":
            error_msg = "❌ Keine Datei ausgewählt."
        else:
            files = {"file": (file_obj.filename, file_obj.read(),
                              file_obj.content_type)}
            try:
                resp = requests.post(f"{BASE_API_URL}/upload_articles",
                                     files=files, timeout=API_TIMEOUT)
            except requests.Timeout:
                resp = None
                error_msg = "Zeitüberschreitung beim Aufruf der API."
            except requests.RequestException as exc:
                resp = None
                error_msg = f"API‑Fehler: {exc}"

            if resp and resp.ok:
                data             = resp.json()
                upload_summary   = data.get("message") or "Import abgeschlossen."
                skipped_suppliers = data.get("missing_suppliers", [])
                flash(upload_summary, "success")
            elif resp:
                # API lieferte Fehlercode
                error_msg = f"❌ Import fehlgeschlagen: {resp.text}"

        if error_msg:
            flash(error_msg, "danger")

    # Render *immer* dieselbe Seite – ggf. mit Result‑Details
    return render_template(
        "upload_excel.html",
        skipped_suppliers = skipped_suppliers,
        upload_summary    = upload_summary,
    )

# ------------------------------------------------------------------
# Upload suppliers Excel
# ------------------------------------------------------------------
@app.route("/suppliers/import", methods=["GET", "POST"])
def import_suppliers():
    if request.method == "POST":
        file_obj = request.files.get("file")
        if not file_obj or file_obj.filename == "":
            flash("❌ Keine Datei ausgewählt.", "danger")
            return redirect(request.url)

        files = {"file": (file_obj.filename, file_obj.read(), file_obj.content_type)}
        resp  = requests.post(f"{BASE_API_URL}/upload_suppliers", files=files)

        if resp.ok:
            flash(f"✅ Import erfolgreich! {resp.json()['message']}", "success")
        else:
            detail = resp.json().get("detail", resp.text)
            flash(f"❌ Import fehlgeschlagen: {detail}", "danger")

        return redirect(url_for("suppliers"))

    return render_template("import_suppliers.html")

# ------------------------------------------------------------------
# Add supplier
# ------------------------------------------------------------------
@app.route("/add_supplier", methods=["GET", "POST"])
def add_supplier():
    if request.method == "POST":
        data = {
            "supplier_number": request.form["supplier_number"],
            "name"           : request.form["name"],
            "address"        : request.form.get("address", ""),
            "email"          : request.form.get("email", "")
        }
        resp = requests.post(f"{BASE_API_URL}/add_supplier", json=data)
        flash(
            "Supplier added successfully!" if resp.ok else "Error adding supplier",
            "success" if resp.ok else "danger"
        )
        return redirect(url_for("suppliers"))

    return render_template("add_supplier.html")

# ─── Kalkulation Seite ───────────────────────────────────────
@app.route("/kalkulation")
def kalkulation():
    return render_template("kalkulation.html")

# ─── Controlling Seite ───────────────────────────────────────
@app.route("/controlling")
def controlling():
    return render_template("controlling.html")


@app.route("/users")
def users():
    if not is_super(): return abort(403)
    return render_template("users.html")

@app.route("/users/create")
def users_create():
    if not is_super(): return abort(403)
    return render_template("user_create.html")
# ------------------------------------------------------------------
# Run locally or via gunicorn
# ------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))     # Render sets $PORT
    app.run(host="0.0.0.0", port=port, debug=True)
