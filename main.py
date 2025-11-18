from datetime import datetime, timezone

from fastapi import FastAPI

from app.api.routes.ai import router as ai_router
from app.api.routes.admin_users import router as admin_users_router
from app.api.routes.auth import router as auth_router
from app.api.routes.menu_admin import router as menu_admin_router
from app.api.routes.menu_public import router as menu_public_router
from app.api.routes.profile import router as profile_router

app = FastAPI(title="AI-Powered Barista API")

app.include_router(auth_router)
app.include_router(admin_users_router)
app.include_router(menu_admin_router)
app.include_router(menu_public_router)
app.include_router(profile_router)
app.include_router(ai_router)


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
