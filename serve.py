# serve.py  – single entry‑point for Render

from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware

# --- import the two existing apps ------------------------------------
from backend_fastapi import app as api_app           # FastAPI backend
from flask_frontend.app import app as flask_app      # Flask frontend

# --- umbrella FastAPI instance ---------------------------------------
root = FastAPI(
    title="Procurement‑UI – combined stack",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# 1) expose the FastAPI back‑end under /api   (all routes stay identical)
root.mount("/api", api_app)

# 2) let every other path fall through to the Flask front‑end
root.mount("/", WSGIMiddleware(flask_app))
