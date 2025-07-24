# serve.py  – single entry‑point for Render

from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware

# ─── import the two apps ─────────────────────────────────────────────
from backend_fastapi import app as api_app           # FastAPI backend
from flask_frontend.app import app as flask_app      # Flask frontend

# ─── umbrella FastAPI instance ───────────────────────────────────────
root = FastAPI(
    title="Procurement‑UI – combined stack",
    docs_url="/api/docs",         # OpenAPI docs live under /api/…
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# mount the FastAPI backend under /api  (all existing routes keep working)
root.mount("/api", api_app)

# let every other path fall through to Flask
root.mount("/", WSGIMiddleware(flask_app))
