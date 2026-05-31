import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from routers import websocket, visitas, rutas, dashboard, roles, geografia, usuarios, catalogo, gestion, auth, gps

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: launch background task for reponedor inactivity monitoring
    task = asyncio.create_task(websocket.check_reponedor_timeouts())
    
    # Startup: launch daily cron for route generation
    from services.cron import run_daily_cron
    cron_task = asyncio.create_task(run_daily_cron())
    
    yield
    # Shutdown: cancel background task
    task.cancel()
    cron_task.cancel()
    try:
        await asyncio.gather(task, cron_task, return_exceptions=True)
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="CampoRuta - Backend",
    description="API para optimización de rutas (v3.0 - Soporte Nacional)",
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
app.include_router(auth.router)
app.include_router(gps.router)
app.include_router(websocket.router)
app.include_router(rutas.router)
app.include_router(visitas.router)
app.include_router(dashboard.router)

# Include new CRUD routers
app.include_router(roles.router)
app.include_router(geografia.router)
app.include_router(usuarios.router)
app.include_router(catalogo.router)
app.include_router(gestion.router)

@app.get("/")
def read_root():
    return {"status": "ok", "proyecto": "CampoRuta", "version": "3.0.0"}
