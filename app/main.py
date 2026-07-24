import logging
from contextlib import asynccontextmanager
from datetime import datetime
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import get_settings
from app.db import create_db_and_tables
from app.routers import admin
from app.scheduler import start_scheduler, stop_scheduler
from app.services.webhook_sender import process_pending_webhooks
from app.db import get_session
import asyncio

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting University Portal Simulator...")
    create_db_and_tables()
    start_scheduler()
    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down...")
    stop_scheduler()
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.app_name,
    description="Mock university portal backend for ERPNext integration demo",
    version="0.1.0",
    lifespan=lifespan,
    debug=settings.debug
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import admin, webhooks

# Include routers
app.include_router(admin.router)
app.include_router(webhooks.router)

# Mount static assets directory
static_dir = os.path.join(os.path.dirname(__file__), "..", "portal-admin-frontend", "dist")

if os.path.isdir(os.path.join(static_dir, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

@app.get("/api-info")
async def root():
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
        "admin": "/admin",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Catch-all route to serve the React SPA and static files"""
    dist_path = os.path.join(static_dir, full_path)
    if os.path.isfile(dist_path):
        return FileResponse(dist_path)
    
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    
    return {"error": "Frontend not built. Run 'npm run build' in portal-admin-frontend."}

# Background task to process webhooks periodically
async def webhook_processor():
    """Periodically process pending webhooks"""
    while True:
        try:
            with next(get_session()) as session:
                await process_pending_webhooks(session)
        except Exception as e:
            logger.error(f"Error processing webhooks: {e}")
        await asyncio.sleep(60)  # Check every minute


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.debug)