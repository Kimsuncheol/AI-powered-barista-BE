from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timezone

app = FastAPI()

class Health(BaseModel):
    status: str
    service: str
    time: str

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}

@app.get("/health", response_model=Health)
def health():
    now = datetime.now(timezone.utc).isoformat()
    return {"status": "ok", "service": "api", "time": now}

@app.get("/ready")
def ready():
    return {"ready": True}

@app.get("/live")
def live():
    return {"alive": True}