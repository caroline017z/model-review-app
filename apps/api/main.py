"""38DN Pricing Model Review — FastAPI Backend."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routers import models, review, walk, benchmarks

app = FastAPI(
    title="38DN Pricing Model Review API",
    version="1.0.0",
    description="API for solar energy pricing model validation, audit, and comparison.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(models.router, prefix="/api/models", tags=["Models"])
app.include_router(review.router, prefix="/api/review", tags=["Review"])
app.include_router(walk.router, prefix="/api/walk", tags=["Walk"])
app.include_router(benchmarks.router, prefix="/api/benchmarks", tags=["Benchmarks"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
