import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from routers.rutas import router as rutas_router
from routers.visitas import router as visitas_router
from routers.dashboard import router as dashboard_router
from routers.websocket import router as websocket_router, check_reponedor_timeouts

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: launch background task for reponedor inactivity monitoring
    task = asyncio.create_task(check_reponedor_timeouts())
    yield
    # Shutdown: cancel background task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="CampoRuta API",
    description="FastAPI Backend — Grupo Venado — CampoRuta v3.0",
    version="3.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(rutas_router)
app.include_router(visitas_router)
app.include_router(dashboard_router)
app.include_router(websocket_router)

@app.get("/")
def read_root():
    return {"status": "ok", "proyecto": "CampoRuta", "version": "3.0.0"}
