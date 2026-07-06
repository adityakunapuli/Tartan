"""FastAPI application and execution entry point for Plaid-Local."""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

from core.db.database import init_db
from core.scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and shutdown lifecycle."""
    init_db()
    start_scheduler()
    yield
    stop_scheduler()

app = FastAPI(title="Plaid-Local API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
def serve_auth_page():
    """Serves the Plaid Link authentication page."""
    with open("auth.html", "r", encoding="utf-8") as f:
        return f.read()

# Include the plaid router
from modules.plaid_integration.router import router as plaid_router
app.include_router(plaid_router)

if __name__ == "__main__":
    # Standard PyCharm driver block
    uvicorn.run(app, host="127.0.0.1", port=8000)
