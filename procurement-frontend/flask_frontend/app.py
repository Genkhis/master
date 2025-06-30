from flask import Flask, render_template, request, redirect, url_for, flash
import requests

app = Flask(__name__, template_folder="templates")
app.secret_key = "0103050709"

BASE_API_URL = "http://127.0.0.1:8001"

# -------------------------------
# Home / Index: Basic article list
# -------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    articles = []
    query = request.args.get("query", "")
    filter_by = request.args.get("filter_by", "")
    if request.method == "POST":
        query = request.form.get("query", "")
        filter_by = request.form.get("filter_by", "")
    response = requests.get(f"{BASE_API_URL}/articles/?query={query}&filter_by={filter_by}")
    if response.status_code == 200:
        articles = response.json()
    else:
        flash("Error fetching articles", "danger")
    return render_template("index.html", articles=articles)

def _extract_filter_lists(form):
    queries = [q.strip() for q in form.getlist("query[]") if q.strip()]
    fields  = form.getlist("filter_by[]")[: len(queries)]
    return queries, fields

@app.route("/all_articles", methods=["GET", "POST"])
def all_articles():
    # 1 – extract filters
    if request.method == "POST":
        queries, fields = _extract_filter_lists(request.form)
    else:
        q = request.args.get("query", "").strip()
        f = request.args.get("filter_by", "")
        queries, fields = ([q] if q else []), ([f] if f else [])

    # pair them up here
    filter_pairs = list(zip(queries, fields))

    # 2 – decide which endpoint to call
    if not filter_pairs:
        resp = requests.get(f"{BASE_API_URL}/articles/")
    elif len(filter_pairs) == 1:
        q, f = filter_pairs[0]
        resp = requests.get(f"{BASE_API_URL}/articles/?query={q}&filter_by={f}")
    else:
        payload = [{"query": q, "field": f} for q, f in filter_pairs]
        resp = requests.post(f"{BASE_API_URL}/articles/advanced", json=payload)

    # 3 – error handling
    if resp.status_code != 200:
        flash("Error fetching articles", "danger")
        articles = []
    else:
        articles = resp.json()

    # 4 – render, passing filter_pairs instead of two separate lists
    return render_template(
        "all-articles.html",
        articles=articles,
        filter_pairs=filter_pairs,
        BASE_API_URL=BASE_API_URL
    )







# -------------------------------
# Add Article
# -------------------------------
@app.route("/add_article", methods=["GET", "POST"])
def add_article():
    if request.method == "POST":
        supplier_number = request.form.get("supplier_number", "").strip() or None
        data = {
    "article_number": request.form["article_number"],
    "article_name": request.form["article_name"],
    "description": request.form["description"],
    "cost_type": request.form["cost_type"],
    "category": request.form["category"],
    "dimension": request.form.get("dimension", ""),
    "item_no_ext": request.form["item_no_ext"],
    "order_number": request.form.get("order_number", ""),
    "item_units": request.form["item_units"],
    "quantity": float(request.form["quantity"]),
    "unit_of_measure": request.form["unit_of_measure"],
    "unit_price": float(request.form["unit_price"]),
    "price_per_unit_of_measure": float(request.form["price_per_unit_of_measure"]),
    "amount": float(request.form["amount"]),
    "delivery": request.form.get("delivery") or None,
    "supplier_number": supplier_number,
    "costplace": request.form.get("costplace") or None   # NEW: fixed key and value retrieval
}


        response = requests.post(f"{BASE_API_URL}/add_article", json=data)
        if response.status_code == 200:
            flash("Article added successfully!", "success")
        else:
            flash("Error adding article", "danger")
        return redirect(url_for("index"))
    return render_template("add_article.html")

# -------------------------------
# Edit Article
# -------------------------------

@app.route("/edit_article/<int:article_id>", methods=["GET", "POST"])
def edit_article(article_id):
    if request.method == "POST":
        supplier_number = request.form.get("supplier_number", "").strip() or None

        data = {
            "article_number"           : request.form.get("article_number"),
            "article_name"             : request.form.get("article_name"),
            "description"              : request.form.get("description"),
            "cost_type"                : request.form.get("cost_type"),
            "category"                 : request.form.get("category"),
            "dimension"                : request.form.get("dimension", ""),
            "item_no_ext"              : request.form.get("item_no_ext"),
            "order_number"             : request.form.get("order_number", ""),
            "item_units"               : request.form.get("item_units"),
            "quantity"                 : float(request.form.get("quantity", 0)),
            "unit_of_measure"          : request.form.get("unit_of_measure"),
            "unit_price"               : float(request.form.get("unit_price", 0)),
            "price_per_unit_of_measure": float(request.form.get("price_per_unit_of_measure", 0)),
            "amount"                   : float(request.form.get("amount", 0)),
            "delivery"                 : request.form.get("delivery") or None,
            "supplier_number"          : supplier_number,
            "costplace"                : request.form.get("costplace") or None,
            # NEW ───────────────────────────────────────────────────────────
            "certification"            : request.form.get("certification") or None
        }

        response = requests.patch(
            f"{BASE_API_URL}/update_article_partial/{article_id}",
            json=data
        )
        flash(
            "Article updated successfully!" if response.status_code == 200
            else f"Error updating article – {response.text}",
            "success" if response.status_code == 200 else "danger"
        )
        return redirect(url_for("index"))

    # initial GET → load article for the edit form
    response = requests.get(f"{BASE_API_URL}/get_article/{article_id}")
    if response.status_code != 200:
        flash("Error retrieving article.", "danger")
        return redirect(url_for("index"))

    return render_template("edit_article.html", article=response.json())

# -------------------------------
# Delete Article
# -------------------------------
@app.route("/delete_article/<int:article_id>")
def delete_article(article_id):
    response = requests.delete(f"{BASE_API_URL}/delete_article/{article_id}")
    if response.status_code == 200:
        flash("Article deleted successfully!", "success")
    else:
        flash(f"Error deleting article: {response.status_code} - {response.text}", "danger")
    return redirect(url_for("index"))


# flask_frontend/app.py  ── price_history()  (replace the whole function)
@app.route("/price_history/<supplier_number>/<item_no_ext>")
def price_history(supplier_number, item_no_ext):
    # ── price history from FastAPI
    hist_resp = requests.get(
        f"{BASE_API_URL}/price_history_by_composite/"
        f"{supplier_number}/{item_no_ext}"
    )
    if hist_resp.status_code != 200:
        flash("Error fetching price history", "danger")
        return redirect(url_for("index"))
    history_data = hist_resp.json()

    # ── supplier master data
    supp_resp = requests.get(f"{BASE_API_URL}/get_supplier/{supplier_number}")
    supplier  = supp_resp.json() if supp_resp.status_code == 200 else None

    return render_template(
        "price_history.html",
        article  = history_data["article"],
        stats    = history_data["stats"],
        history  = history_data["price_history"],
        supplier = supplier                         # <── NEW
    )







# ------------------------------------------------------------------
#  Supplier list with search + pagination (A→Z)
# ------------------------------------------------------------------
@app.route("/suppliers")
def suppliers():
    PAGE_SIZE = 40                              # 30 or 40 – pick your poison
    page  = max(1, int(request.args.get("page", 1)))
    query = request.args.get("query", "").strip().lower()

    # 1) fetch all suppliers from FastAPI
    resp = requests.get(f"{BASE_API_URL}/suppliers")
    if resp.status_code != 200:
        flash("Error fetching suppliers", "danger")
        return render_template(
            "suppliers.html",
            suppliers=[],
            page=1,
            total_pages=1,
            query=query
        )
    suppliers = resp.json()

    # 2) sort A → Z
    suppliers.sort(key=lambda s: (s.get("name") or "").lower())

    # 3) optional search filter
    if query:
        suppliers = [
            s for s in suppliers
            if query in (s.get("name") or "").lower()
        ]

    # 4) pagination
    total_pages = max(1, (len(suppliers) + PAGE_SIZE - 1) // PAGE_SIZE)
    suppliers   = suppliers[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]

    return render_template(
        "suppliers.html",
        suppliers=suppliers,
        page=page,
        total_pages=total_pages,
        query=query
    )


# -------------------------------
# Supplier Articles Page
# -------------------------------
@app.route("/supplier_articles/<supplier_number>")
def supplier_articles(supplier_number):
    # First, retrieve the supplier details.
    supplier_response = requests.get(f"{BASE_API_URL}/get_supplier/{supplier_number}")
    if supplier_response.status_code == 200:
        supplier = supplier_response.json()
    else:
        flash("Error fetching supplier details", "danger")
        supplier = None

    # Then, retrieve the articles for that supplier.
    articles_response = requests.get(f"{BASE_API_URL}/supplier_articles/{supplier_number}")
    if articles_response.status_code == 200:
        articles = articles_response.json()
    else:
        flash("Error fetching supplier articles", "danger")
        articles = []

    # Pass both the supplier and articles to the template.
    return render_template("supplier_articles.html", supplier=supplier, articles=articles)


@app.route("/upload_excel", methods=["GET", "POST"])
def upload_excel():
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file part in the request", "danger")
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            flash("No file selected", "danger")
            return redirect(request.url)
        # Prepare the file for upload to the FastAPI backend.
        files = {"file": (file.filename, file.read(), file.content_type)}
        response = requests.post(f"{BASE_API_URL}/upload_articles", files=files)
        if response.status_code == 200:
            flash("Excel file uploaded successfully!", "success")
        else:
            flash(f"Error uploading file: {response.text}", "danger")
        return redirect(url_for("index"))
    return render_template("upload_excel.html")


# app.py  ────────────────────────────────────────────────────────────────
@app.route("/suppliers/import", methods=["GET", "POST"])
def import_suppliers():
    """
    Upload an Excel list of suppliers and forward it to FastAPI.
    Shows a green flash on success and a red one on failure.
    """
    if request.method == "POST":
        # ── basic browser-side validation ───────────────────────────────
        if "file" not in request.files:
            flash("❌ Kein Datei-Feld gefunden.", "danger")
            return redirect(request.url)

        file_obj = request.files["file"]
        if file_obj.filename == "":
            flash("❌ Keine Datei ausgewählt.", "danger")
            return redirect(request.url)

        # ── forward file to FastAPI backend ─────────────────────────────
        files = {"file": (file_obj.filename, file_obj.read(), file_obj.content_type)}
        resp  = requests.post(f"{BASE_API_URL}/upload_suppliers", files=files)

        if resp.ok:
            j = resp.json()   # e.g. {"message":"processed 18 row(s)", ...}
            flash(f"✅ Import erfolgreich! {j['message']}", "success")
        else:
            # FastAPI returns {"detail": "..."} for validation errors
            detail = resp.json().get("detail", resp.text)
            flash(f"❌ Import fehlgeschlagen: {detail}", "danger")

        return redirect(url_for("suppliers"))

    # GET → show the upload form
    return render_template("import_suppliers.html")




@app.route("/add_supplier", methods=["GET", "POST"])
def add_supplier():
    if request.method == "POST":
        data = {
            "supplier_number": request.form["supplier_number"],
            "name": request.form["name"],
            "address": request.form.get("address", ""),
            "email": request.form.get("email", "")
        }
        response = requests.post(f"{BASE_API_URL}/add_supplier", json=data)
        if response.status_code == 200:
            flash("Supplier added successfully!", "success")
        else:
            flash("Error adding supplier", "danger")
        return redirect(url_for("suppliers"))
    return render_template("add_supplier.html")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
