import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import SQLAlchemyError

from database import Base, engine
from rate_limiter import limiter
from routes import admin, auth, complaints, dashboard, transparency

app = FastAPI(title="CityShakti PS-CRM")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

import os

# Secure CORS: Allow localhost by default, but pull Vercel/Prod URLs from .env
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https?://(?:localhost|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|127\.0\.0\.1)(?::\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("cityshakti")
logging.basicConfig(level=logging.INFO)


@app.get("/api/health", tags=["System"])
def health_check():
    return {"status": "ok", "version": "1.0.1"}


@app.on_event("startup")
def on_startup():
    import subprocess
    from security import hash_password
    from database import SessionLocal
    from models import User

    try:
        logger.info("Running Alembic Migrations...")
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        logger.info("Migrations completed successfully.")
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")

    # Seed the Sudo Account
    try:
        db = SessionLocal()
        sudo_email = "sudo@cityshakti.com"
        existing_sudo = db.query(User).filter(User.email == sudo_email).first()
        if not existing_sudo:
            sudo_user = User(
                full_name="Sudo User",
                email=sudo_email,
                password_hash=hash_password("adminpassword"),
                role="sudo",
                is_active=True
            )
            db.add(sudo_user)
            db.commit()
            logger.info("Successfully created pre-declared Sudo account: sudo@cityshakti.com")
    except Exception as e:
        logger.error(f"Failed to create Sudo user: {e}")
    finally:
        db.close()


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(_: Request, exc: SQLAlchemyError):
    logger.exception("Database error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Database operation failed",
            "code": "DB_ERROR",
            "details": str(exc)
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "Validation failed",
            "code": "VALIDATION_ERROR",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "An unexpected server error occurred.",
            "code": "INTERNAL_ERROR",
            "details": str(exc)
        },
    )


app.include_router(auth.router)
app.include_router(complaints.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(transparency.router)
