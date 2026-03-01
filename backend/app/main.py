"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import users, profiles, jd, resumes

# Create all tables on startup (dev convenience; use Alembic in production)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="OneResume",
    description="AI-Powered Role-Specific Resume Generation Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(profiles.router, prefix="/api/profiles", tags=["Profiles"])
app.include_router(jd.router, prefix="/api/jd", tags=["Job Descriptions"])
app.include_router(resumes.router, prefix="/api/resumes", tags=["Resumes"])


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "app": "OneResume"}
