"""
app/main.py

FastAPI backend implementing all APIs from the AI Benefits Optimizer + Trends Engine spec.
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.database import engine, Base
from app.api.endpoints import users, paystubs, benefits, trends, kestra_hooks, notifications_admin

# Create tables (for local dev; skip if using Supabase migrations)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Benefits Optimizer API",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # lock down in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve local frontend files
project_root = Path(__file__).resolve().parent.parent
static_path = project_root / "static"
static_path.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

API_PREFIX = "/api/v1"

# Include Routers
app.include_router(users.router, prefix=f"{API_PREFIX}", tags=["Users"])
app.include_router(paystubs.router, prefix=f"{API_PREFIX}/paystubs", tags=["Paystubs"])
app.include_router(benefits.router, prefix=f"{API_PREFIX}/benefits", tags=["Benefits"])
app.include_router(trends.router, prefix=f"{API_PREFIX}", tags=["Trends"])
app.include_router(kestra_hooks.router, prefix=f"{API_PREFIX}/kestra", tags=["Kestra Workflows"])
app.include_router(notifications_admin.router, prefix=f"{API_PREFIX}", tags=["Admin Notifications"])

@app.get("/", include_in_schema=False)
def root():
    return JSONResponse(
        {"message": "AI Benefits Optimizer API", "docs": f"{API_PREFIX}/docs", "openapi": f"{API_PREFIX}/openapi.json"}
    )
