# serve.py  – entry‑point for Render
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware

# import your existing apps
from backend_fastapi import app as api_app          # <- FastAPI backend
from flask_frontend.app import app as flask_app     # <- Flask frontend

root = FastAPI(
    title="Procurement‑UI – combined",
    docs_url=None, redoc_url=None, openapi_url=None     # docs stay under /api/docs
)

# mount the API under /api  (keeps all current routes unchanged)
root.mount("/api", api_app)

# make ALL other paths fall through to Flask
root.mount("/", WSGIMiddleware(flask_app))
