from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from routers.rutas import router as rutas_router
from routers.visitas import router as visitas_router
from routers.dashboard import router as dashboard_router
from routers.websocket import router as websocket_router

app = FastAPI(
    title="CampoRuta API",
    description="FastAPI Backend con base de datos Supabase",
    version="2.0.0"
)

# CORS configuration - open to all origins (hackathon requirement)
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
    return {"status": "ok", "proyecto": "CampoRuta"}
