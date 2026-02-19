import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import admin, auth, export, groups, hotels, reviews

load_dotenv()

app = FastAPI(title="Kasa Reputation Dashboard")

# CORS
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables
Base.metadata.create_all(bind=engine)

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(hotels.router, prefix="/api/hotels", tags=["hotels"])
app.include_router(groups.router, prefix="/api/groups", tags=["groups"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["reviews"])
app.include_router(export.router, prefix="/api/export", tags=["export"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
