from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import logging
import asyncio
from datetime import datetime, timezone

from database import SessionLocal
import models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Maps reponedor_id -> active WebSocket
        self.reponedor_connections: Dict[str, WebSocket] = {}
        # Maps supervisor_id -> list of active WebSockets
        self.supervisor_connections: Dict[str, List[WebSocket]] = {}
        # Stores state for each reponedor:
        # { reponedor_id: { "lat": float, "lon": float, "pdv_actual": str, "ultimo_update": datetime, "timestamp_client": str, "estado": str } }
        self.reponedor_states: Dict[str, Dict[str, Any]] = {}

    async def connect_reponedor(self, reponedor_id: str, websocket: WebSocket):
        await websocket.accept()
        self.reponedor_connections[reponedor_id] = websocket
        logger.info(f"Reponedor WS connected: {reponedor_id}")
        
        # Initialize state if it doesn't exist
        if reponedor_id not in self.reponedor_states:
            self.reponedor_states[reponedor_id] = {
                "lat": 0.0,
                "lon": 0.0,
                "pdv_actual": "",
                "ultimo_update": datetime.now(timezone.utc),
                "timestamp_client": "",
                "estado": "desconectado"
            }

    def disconnect_reponedor(self, reponedor_id: str):
        if reponedor_id in self.reponedor_connections:
            del self.reponedor_connections[reponedor_id]
        logger.info(f"Reponedor WS disconnected: {reponedor_id}")

    async def connect_supervisor(self, supervisor_id: str, websocket: WebSocket):
        await websocket.accept()
        if supervisor_id not in self.supervisor_connections:
            self.supervisor_connections[supervisor_id] = []
        self.supervisor_connections[supervisor_id].append(websocket)
        logger.info(f"Supervisor WS connected: {supervisor_id}. Total active for supervisor: {len(self.supervisor_connections[supervisor_id])}")
        
        # Send initial state immediately
        await self.send_supervisor_update(supervisor_id, websocket)

    def disconnect_supervisor(self, supervisor_id: str, websocket: WebSocket):
        if supervisor_id in self.supervisor_connections:
            if websocket in self.supervisor_connections[supervisor_id]:
                self.supervisor_connections[supervisor_id].remove(websocket)
                logger.info(f"Supervisor WS disconnected: {supervisor_id}. Remaining active: {len(self.supervisor_connections[supervisor_id])}")
                if not self.supervisor_connections[supervisor_id]:
                    del self.supervisor_connections[supervisor_id]

    async def update_reponedor_state(self, reponedor_id: str, data: Dict[str, Any]):
        # Update internal memory state
        self.reponedor_states[reponedor_id] = {
            "lat": float(data.get("lat", 0.0)),
            "lon": float(data.get("lon", 0.0)),
            "pdv_actual": str(data.get("pdv_actual", "")),
            "ultimo_update": datetime.now(timezone.utc),
            "timestamp_client": str(data.get("timestamp", "")),
            "estado": "activo"
        }
        
        # Save to database positions_gps and update PerfilReponedor
        db = SessionLocal()
        try:
            rid_int = int(reponedor_id)
            pos = models.PosicionGPS(
                id_reponedor=rid_int,
                latitud=float(data.get("lat", 0.0)),
                longitud=float(data.get("lon", 0.0)),
                timestamp=datetime.utcnow()
            )
            db.add(pos)
            
            perfil = db.query(models.PerfilReponedor).filter(models.PerfilReponedor.id_usuario == rid_int).first()
            if perfil:
                perfil.lat_actual = float(data.get("lat", 0.0))
                perfil.lon_actual = float(data.get("lon", 0.0))
                perfil.online = True
                perfil.ultima_conexion = datetime.utcnow()
                db.add(perfil)
            db.commit()
        except Exception as e:
            logger.error(f"Error updating database tracking for reponedor {reponedor_id}: {e}")
        finally:
            db.close()
            
        # Determine supervisor and broadcast update
        supervisor_id = self.get_supervisor_of_reponedor(reponedor_id)
        if supervisor_id:
            await self.broadcast_supervisor_update(supervisor_id)

    async def broadcast_supervisor_update(self, supervisor_id: str):
        if supervisor_id not in self.supervisor_connections:
            return
            
        payload = self.build_supervisor_payload(supervisor_id)
        for ws in list(self.supervisor_connections[supervisor_id]):
            try:
                await ws.send_json(payload)
            except Exception as e:
                logger.error(f"Error sending update to supervisor {supervisor_id}: {e}")
                self.disconnect_supervisor(supervisor_id, ws)

    async def send_supervisor_update(self, supervisor_id: str, websocket: WebSocket):
        payload = self.build_supervisor_payload(supervisor_id)
        try:
            await websocket.send_json(payload)
        except Exception as e:
            logger.error(f"Error sending initial state to supervisor {supervisor_id}: {e}")

    def build_supervisor_payload(self, supervisor_id: str) -> Dict[str, Any]:
        rep_ids = self.get_reponedores_for_supervisor(supervisor_id)
        reponedores_payload = []
        for rid in rep_ids:
            state = self.reponedor_states.get(rid, {
                "lat": 0.0,
                "lon": 0.0,
                "pdv_actual": "",
                "timestamp_client": "",
                "estado": "desconectado"
            })
            reponedores_payload.append({
                "id": rid,
                "lat": state["lat"],
                "lon": state["lon"],
                "estado": state["estado"],
                "pdv_actual": state["pdv_actual"],
                "ultimo_update": state["timestamp_client"] or "Nunca"
            })
        return {"reponedores": reponedores_payload}

    def get_supervisor_of_reponedor(self, reponedor_id: str) -> str:
        db = SessionLocal()
        try:
            rep = db.query(models.Usuario).filter(models.Usuario.id_usuario == int(reponedor_id)).first()
            return str(rep.id_supervisor) if (rep and rep.id_supervisor) else None
        except Exception as e:
            logger.error(f"Error finding supervisor for reponedor {reponedor_id}: {e}")
            return None
        finally:
            db.close()

    def get_reponedores_for_supervisor(self, supervisor_id: str) -> List[str]:
        db = SessionLocal()
        try:
            reps = db.query(models.Usuario.id_usuario).filter(
                models.Usuario.id_supervisor == int(supervisor_id)
            ).all()
            return [str(r[0]) for r in reps]
        except Exception as e:
            logger.error(f"Error querying reponedores for supervisor {supervisor_id}: {e}")
            return []
        finally:
            db.close()

    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcasting standard message to all active supervisors and reponedores.
        """
        for ws in self.reponedor_connections.values():
            try:
                await ws.send_json(message)
            except Exception:
                pass
        for ws_list in self.supervisor_connections.values():
            for ws in ws_list:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass

# Singleton instance of the connection manager
manager = ConnectionManager()

router = APIRouter(
    prefix="/ws",
    tags=["WebSocket"]
)

# Background task to monitor inactivity (5 minutes timeout)
async def check_reponedor_timeouts():
    while True:
        await asyncio.sleep(10)  # Check every 10 seconds
        try:
            now = datetime.now(timezone.utc)
            db = SessionLocal()
            try:
                for rep_id, state in list(manager.reponedor_states.items()):
                    if state["estado"] == "activo":
                        elapsed = (now - state["ultimo_update"]).total_seconds()
                        if elapsed > 300:  # 5 minutes (300 seconds)
                            state["estado"] = "sin_señal"
                            logger.warning(f"Reponedor {rep_id} marked as 'sin_señal' due to inactivity")
                            
                            # Update DB
                            perfil = db.query(models.PerfilReponedor).filter(models.PerfilReponedor.id_usuario == int(rep_id)).first()
                            if perfil:
                                perfil.online = False
                                db.add(perfil)
                                db.commit()
                            
                            # Broadcast to supervisor
                            supervisor_id = manager.get_supervisor_of_reponedor(rep_id)
                            if supervisor_id:
                                await manager.broadcast_supervisor_update(supervisor_id)
            except Exception as e:
                logger.error(f"Error inside check_reponedor_timeouts: {e}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error checking reponedor timeouts: {e}")

@router.websocket("/reponedor/{reponedor_id}")
async def websocket_reponedor(websocket: WebSocket, reponedor_id: str):
    await manager.connect_reponedor(reponedor_id, websocket)
    try:
        while True:
            # Expected incoming format: {"lat": float, "lon": float, "timestamp": str, "pdv_actual": str}
            data = await websocket.receive_json()
            await manager.update_reponedor_state(reponedor_id, data)
    except WebSocketDisconnect:
        manager.disconnect_reponedor(reponedor_id)
    except Exception as e:
        logger.error(f"WebSocket reponedor {reponedor_id} error: {e}")
        manager.disconnect_reponedor(reponedor_id)

@router.websocket("/supervisor/{supervisor_id}")
async def websocket_supervisor(websocket: WebSocket, supervisor_id: str):
    await manager.connect_supervisor(supervisor_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_supervisor(supervisor_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket supervisor {supervisor_id} error: {e}")
        manager.disconnect_supervisor(supervisor_id, websocket)
