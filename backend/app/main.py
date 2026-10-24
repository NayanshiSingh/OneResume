"""FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.errors import ConflictError, InvalidRequestError, NotFoundError, ProviderUnavailableError
from app.routers import auth, profiles, jd, resumes

# Schema is managed by Alembic: run `alembic upgrade head` before starting the app.

app = FastAPI(
    title="OneResume",
    description="AI-Powered Role-Specific Resume Generation Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@app.middleware("http")
async def reject_cross_site_writes(request: Request, call_next):
    """Cookie sessions need CSRF protection: refuse state changes from other origins."""
    origin = request.headers.get("origin")
    if request.method not in SAFE_METHODS and origin and origin not in settings.ALLOWED_ORIGINS:
        return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
    return await call_next(request)


@app.exception_handler(NotFoundError)
async def not_found(_: Request, exc: NotFoundError):
    return JSONResponse({"detail": str(exc)}, status_code=404)


@app.exception_handler(ConflictError)
async def conflict(_: Request, exc: ConflictError):
    return JSONResponse({"detail": str(exc)}, status_code=409)


@app.exception_handler(InvalidRequestError)
async def invalid_request(_: Request, exc: InvalidRequestError):
    return JSONResponse({"detail": str(exc)}, status_code=422)


@app.exception_handler(ProviderUnavailableError)
async def provider_unavailable(_: Request, exc: ProviderUnavailableError):
    return JSONResponse({"detail": str(exc)}, status_code=503)


# ── Routers ───────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/auth", tags=["Accounts"])
app.include_router(profiles.router, prefix="/api/profile", tags=["Profile"])
app.include_router(jd.router, prefix="/api/jd", tags=["Job Descriptions"])
app.include_router(resumes.router, prefix="/api/resumes", tags=["Resumes"])


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "app": "OneResume"}
