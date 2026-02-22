"""
═══════════════════════════════════════════════════════════════════════════════
FILE: main.py
PURPOSE: FastAPI application entry point and configuration
═══════════════════════════════════════════════════════════════════════════════

WHAT THIS FILE DOES:
- Initializes FastAPI application
- Registers all route modules (phishing, analytics)
- Configures CORS for frontend communication
- Sets up logging
- Provides health check endpoint
- Serves API documentation (Swagger UI)

WHAT IT CONNECTS TO:
- config.py: Uses app settings and CORS configuration
- routes/phishing.py: Registers phishing endpoints
- routes/analytics.py: Registers analytics endpoints
- All services: Imported via routes

ARCHITECTURE:
    main.py is the "hub" that:
    1. Creates FastAPI app
    2. Registers routes (phishing, analytics)
    3. Configures CORS
    4. Starts server on port 8000
    
    Then incoming HTTP requests flow through:
    routes -> services -> api_client/database

FEATURES:
    - Auto-generated Swagger UI at: http://localhost:8000/docs
    - JSON Schema at: http://localhost:8000/openapi.json
    - CORS enabled for frontend communication
    - Health check endpoint: GET /health
    - Info endpoint: GET /info

HOW TO USE:
    To run the backend:
    
    # From backend/ directory:
    python main.py
    
    # Or with uvicorn directly:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    
    Then access:
    - API: http://localhost:8000/api/*
    - Docs: http://localhost:8000/docs
    - Frontend: http://localhost:3000

═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import config
from routes import phishing, analytics

# Configure logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# INITIALIZE FASTAPI APPLICATION
# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="Backend API for Phish 'N Heat - Global Phishing Tracker",
    docs_url="/docs",  # Swagger UI at /docs
    openapi_url="/openapi.json",  # JSON schema
    redoc_url="/redoc"  # ReDoc at /redoc
)

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURE CORS (Cross-Origin Resource Sharing)
# ──────────────────────────────────────────────────────────────────────────────
# This allows the frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        config.FRONTEND_ORIGIN,
        "http://localhost:3000",  # Local development
        "http://localhost:8000",  # Same host testing
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

logger.info(f"CORS enabled for: {config.FRONTEND_ORIGIN}")

# ──────────────────────────────────────────────────────────────────────────────
# REGISTER ROUTE MODULES
# ──────────────────────────────────────────────────────────────────────────────
# These register all API endpoints

app.include_router(
    phishing.router,
    prefix="/api",
    tags=["phishing"],
    responses={404: {"description": "Not found"}}
)

app.include_router(
    analytics.router,
    prefix="/api",
    tags=["analytics"],
    responses={404: {"description": "Not found"}}
)

logger.info("✓ Route modules registered")

# ──────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK ENDPOINT
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    
    Returns server status and version info.
    
    Returns:
        Status dictionary
    
    Example:
        GET /health
        
        Response:
        {
            "status": "healthy",
            "app_name": "Phish 'N Heat Backend",
            "version": "1.0.0",
            "timestamp": "2026-02-21T10:30:00Z"
        }
    """
    return {
        "status": "healthy",
        "app_name": config.APP_NAME,
        "version": config.APP_VERSION,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/info")
async def app_info():
    """
    Get application information.
    
    Returns detailed information about the backend application.
    
    Returns:
        Application metadata
    
    Example:
        GET /info
        
        Response:
        {
            "name": "Phish 'N Heat Backend",
            "version": "1.0.0",
            "description": "Backend API for phishing threat visualization",
            "api_base": "/api",
            "docs_url": "/docs",
            "endpoints": {
                "phishing": "/api/phishing/...",
                "analytics": "/api/analytics/..."
            }
        }
    """
    return {
        "name": config.APP_NAME,
        "version": config.APP_VERSION,
        "description": "Backend API for Phish 'N Heat - Global Phishing Tracker",
        "api_base": "/api",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "endpoints": {
            "phishing": {
                "all": "/api/phishing/",
                "heatmap": "/api/phishing/heatmap",
                "filtered": "/api/phishing/filtered",
                "stats": "/api/phishing/stats",
                "refresh": "/api/phishing/refresh"
            },
            "analytics": {
                "overview": "/api/analytics/overview",
                "threat_distribution": "/api/analytics/threat-distribution",
                "top_regions": "/api/analytics/top-regions",
                "top_companies": "/api/analytics/top-companies",
                "hotspots": "/api/analytics/threat-hotspots",
                "isp_rankings": "/api/analytics/isp-rankings"
            }
        }
    }


# ──────────────────────────────────────────────────────────────────────────────
# ROOT ENDPOINT
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """
    Root endpoint - redirects to documentation.
    
    Returns:
        Welcome message and links to documentation
    
    Example:
        GET /
        
        Response:
        {
            "message": "Welcome to Phish 'N Heat Backend",
            "docs": "/docs",
            "info": "/info",
            "health": "/health"
        }
    """
    return {
        "message": f"Welcome to {config.APP_NAME} v{config.APP_VERSION}",
        "docs": "/docs",
        "info": "/info",
        "health": "/health"
    }


# ──────────────────────────────────────────────────────────────────────────────
# APPLICATION STARTUP
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting {config.APP_NAME} v{config.APP_VERSION}")
    logger.info(f"Listening on {config.BACKEND_HOST}:{config.BACKEND_PORT}")
    logger.info(f"Documentation: http://{config.BACKEND_HOST}:{config.BACKEND_PORT}/docs")
    
    # Run the server
    uvicorn.run(
        app,
        host=config.BACKEND_HOST,
        port=config.BACKEND_PORT,
        log_level=config.LOG_LEVEL.lower()
    )
