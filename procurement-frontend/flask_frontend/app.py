from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os, requests

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
# Config: API URL (Render vs local)
# ───────────────────────────

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'sqlite:///app.db'  # fallback for local development
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

BASE_API_URL = os.getenv("API_URL", "http://127.0.0.1:8001")
app.config["API_URL"] = BASE_API_URL   # expose for templates & JS
# make {{ API_URL }} available in *all* templates
@app.context_processor
def inject_api_url():
    return {"API_URL": app.config["API_URL"]}

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
# Home
@app.route("/", methods=["GET", "POST"])
def index():
    query     = request.args.get("query", "")
    filter_by = request.args.get("filter_by", "")
    if request.method == "POST":
        query     = request.form.get("query", "")
        filter_by = request.form.get("filter_by", "")

    resp = requests.get(
        f"{BASE_API_URL}/articles/?query={query}&filter_by={filter_by}"
    )
    articles = resp.json() if resp.ok else []
    if not resp.ok:
        flash("Error fetching articles", "danger")

    return render_template("index.html", articles=articles)


# All articles (search + filters)
@app.route("/all_articles", methods=["GET", "POST"])
def all_articles():
    if request.method == "POST":
        queries, fields = _extract_filter_lists(request.form)
    else:
        q = request.args.get("query", "").strip()
        f = request.args.get("filter_by", "")
        queries, fields = ([q] if q else []), ([f] if f else [])

    filter_pairs = list(zip(queries, fields))

    if not filter_pairs:
        resp = requests.get(f"{BASE_API_URL}/articles/")
    elif len(filter_pairs) == 1:
        q, f = filter_pairs[0]
        resp = requests.get(f"{BASE_API_URL}/articles/?query={q}&filter_by={f}")
    else:
        payload = [{"query": q, "field": f} for q, f in filter_pairs]
        resp = requests.post(f"{BASE_API_URL}/articles/advanced", json=payload)

    articles = resp.json() if resp.ok else []
    if not resp.ok:
        flash("Error fetching articles", "danger")

    return render_template(
        "all-articles.html",
        articles=articles,
        filter_pairs=filter_pairs,
    )


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
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("No file selected", "danger")
            return redirect(request.url)

        files = {"file": (file.filename, file.read(), file.content_type)}
        resp  = requests.post(f"{BASE_API_URL}/upload_articles", files=files)

        flash(
            "Excel file uploaded successfully!" if resp.ok
            else f"Error uploading file: {resp.text}",
            "success" if resp.ok else "danger"
        )
        return redirect(url_for("index"))

    return render_template("upload_excel.html")


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
@app.route('/kalkulation')
def kalkulation():
    # TODO: lade hier beliebige Daten für die Kalkulation
    return render_template('kalkulation.html')


# ─── Controlling Seite ───────────────────────────────────────
@app.route('/controlling')
def controlling():
    # TODO: lade hier Reports, Kennzahlen-Info etc.
    return render_template('controlling.html')
# ------------------------------------------------------------------
# Run locally or via gunicorn
# ------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))     # Render sets $PORT
    app.run(host="0.0.0.0", port=port, debug=True)
