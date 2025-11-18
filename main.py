import logging
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes.ai import router as ai_router
from app.api.routes.admin_analytics import router as admin_analytics_router
from app.api.routes.admin_menu import router as admin_menu_router
from app.api.routes.admin_orders import router as admin_orders_router
from app.api.routes.admin_users import router as admin_users_router
from app.api.routes.auth import router as auth_router
from app.api.routes.cart import router as cart_router
from app.api.routes.menu_public import router as menu_public_router
from app.api.routes.orders import router as orders_router
from app.api.routes.order_ws import router as order_ws_router
from app.api.routes.payments import router as payments_router
from app.api.routes.profile import router as profile_router
from app.api.routes.recommendations import router as recommendations_router
from app.core.config import settings
from app.core.logging import configure_logging

# NFR-BE-1 Performance / NFR-BE-4 Scalability:
# Recommended production command:
#   gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4
# Configure keep-alive & timeouts at the process manager/load balancer level.

configure_logging()
logger = logging.getLogger("app")

app = FastAPI(title="AI-Powered Barista API")


@app.middleware("http")
async def enforce_https_middleware(request: Request, call_next):
    """
    SECURITY: ensure HTTPS termination upstream. Optionally enforce via header.

    In production, terminate TLS at the load balancer/ingress and forward
    X-Forwarded-Proto. When FORCE_HTTPS is enabled, requests coming over http
    will be rejected.
    """

    if settings.FORCE_HTTPS:
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        if proto != "https":
            return JSONResponse(
                status_code=400,
                content={"detail": "HTTPS is required"},
            )
    return await call_next(request)


def _format_error(detail: str):
    return {"detail": detail}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(
        "HTTP error",
        extra={"path": request.url.path, "status": exc.status_code},
    )
    return JSONResponse(status_code=exc.status_code, content=_format_error(str(exc.detail)))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Validation error", extra={"path": request.url.path})
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error", exc_info=exc, extra={"path": request.url.path})
    return JSONResponse(
        status_code=500,
        content=_format_error("Internal server error"),
    )

app.include_router(auth_router)
app.include_router(admin_users_router)
app.include_router(admin_menu_router)
app.include_router(admin_orders_router)
app.include_router(admin_analytics_router)
app.include_router(menu_public_router)
app.include_router(profile_router)
app.include_router(ai_router)
app.include_router(recommendations_router)
app.include_router(cart_router)
app.include_router(orders_router)
app.include_router(order_ws_router)
app.include_router(payments_router)


@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}


@app.get("/health")
def health():
    now = datetime.now(timezone.utc).isoformat()
    return {"status": "ok", "service": "api", "time": now}


@app.get("/ready")
def ready():
    return {"ready": True}


@app.get("/live")
def live():
    return {"alive": True}
