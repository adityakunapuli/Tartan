"""FastAPI application and execution entry point for Plaid-Local."""
import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from core.db.database import init_db
from core.scheduler import start_scheduler, stop_scheduler

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


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
    return {"status": "ok"}


from modules.plaid_integration.router import router as plaid_router
from modules.dashboard.router import router as dashboard_router
app.include_router(plaid_router)
app.include_router(dashboard_router)


# Serve the Vite build (must be last — after API routes — so /health, /api, /plaid take priority)
if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:
    @app.get("/", response_class=HTMLResponse)
    def serve_auth_page():
        with open("auth.html", encoding="utf-8") as f:
            return f.read()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
