"""
Main Application Entrypoint
FastAPI Application for Personal Voice Translation Realtime Engine with Secure Transport,
Dynamic WebRTC ICE/STUN/TURN Configuration, and Security Headers Middleware.
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.auth_routes import router as auth_router
from backend.api.realtime_routes import router as realtime_router
from backend.api.voice_routes import router as voice_router
from backend.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Real-time Personal Voice Translation Platform with low latency, voice identity preservation, and session isolation.",
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "microphone=(self), camera=()"
    return response

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth_router)
app.include_router(voice_router)
app.include_router(realtime_router)


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "target_latency_budget_ms": settings.target_latency_budget_ms,
        "offline_mode": settings.offline_mode,
        "local_only": settings.local_only,
        "providers": {
            "stt": settings.stt_provider,
            "translation": settings.translation_provider,
            "tts": settings.tts_provider,
        },
    }


@app.get("/api/config/ice-servers")
async def get_ice_servers():
    """Returns dynamic WebRTC ICE configuration (STUN/TURN) configured for this environment."""
    servers = [{"urls": settings.stun_server_url}]
    if settings.turn_server_url:
        turn_entry = {"urls": settings.turn_server_url}
        if settings.turn_username:
            turn_entry["username"] = settings.turn_username
        if settings.turn_credential:
            turn_entry["credential"] = settings.turn_credential
        servers.append(turn_entry)
    return {"iceServers": servers}


# Mount frontend static directory if exists
frontend_path = Path(__file__).resolve().parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.host, port=settings.port, reload=settings.debug)
