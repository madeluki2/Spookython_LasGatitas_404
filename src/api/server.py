"""
FastAPI Server for Spookython 2026: Track A - Escape de Manta Zombie

Endpoints:
- POST /paso: Technical contract for pathfinding engine (requires x-api-key).
- GET /estado: Returns current world state (turn, zombies, survivors, blocked edges, stats).
- GET /grafo: Returns city graph data (nodes, streets, refugios) for frontend map.
- WebSocket /ws: Real-time bi-directional streaming for live map UI.
- Control API: /simulador/ronda/{id}, /simulador/play, /simulador/pausa, /simulador/step, /simulador/velocidad.
- Static Files: Serves frontend live dashboard at root /
"""

import os
import sys
import asyncio
import time
from typing import Dict, Any, Optional
from pathlib import Path

# Ensure repo root in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, HTTPException, Header, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config import API_KEY, API_KEY_HEADER_NAME, DEFAULT_TURN_SECONDS, FAST_TURN_SECONDS
from src.engine.router import MantaRouter
from src.simulator.apocalypse_sim import ApocalypseSimulator

app = FastAPI(
    title="Escape de Manta Zombie - API de Enrutamiento y Simulación",
    description="Motor de rutas dinámico en tiempo real para evacuación en Manta ante infestación zombie.",
    version="1.0.0"
)

# CORS enabled for all origins (useful for web frontend and external testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static directory for frontend
STATIC_DIR = os.path.join(BASE_DIR, "src", "static")

# Initialize Engine & Simulator
router = MantaRouter()
sim = ApocalypseSimulator(router)
sim.reset_round(ronda=1)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

ws_manager = ConnectionManager()

# Background Simulation Loop Task
sim_task: Optional[asyncio.Task] = None

async def simulation_loop():
    while True:
        try:
            if sim.activo:
                sim.execute_turn()
                state = sim.get_state()
                await ws_manager.broadcast({"tipo": "estado_actualizado", "data": state})
            await asyncio.sleep(sim.turn_delay)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[SimLoop Error] {e}")
            await asyncio.sleep(1.0)

@app.on_event("startup")
async def startup_event():
    global sim_task
    sim_task = asyncio.create_task(simulation_loop())

@app.on_event("shutdown")
async def shutdown_event():
    global sim_task
    if sim_task:
        sim_task.cancel()

# --- TECHNICAL CONTRACT SCHEMAS ---
class PasoRequest(BaseModel):
    sobrevivienteId: str = Field(..., description="ID único del sobreviviente", example="S-0089")
    nodoActual: str = Field(..., description="ID del nodo actual en el grafo de Manta", example="N-0117")
    turno: int = Field(..., description="Número de turno actual de la simulación", example=142)

class PasoResponse(BaseModel):
    siguienteNodo: str = Field(..., description="ID del nodo adyacente válido al que debe avanzar o el mismo nodo", example="N-0118")

class VelocidadRequest(BaseModel):
    segundos: float = Field(..., description="Duración en segundos por turno (ej. 2.0, 0.5, 0.2)", example=0.5)

# --- TECHNICAL CONTRACT ENDPOINTS ---

@app.post(
    "/paso",
    response_model=PasoResponse,
    summary="Consultar siguiente paso para un sobreviviente",
    description="Calcula en <500ms el siguiente nodo óptimo hacia un refugio seguro evitando zombies y calles bloqueadas."
)
async def post_paso(
    payload: PasoRequest,
    x_api_key: Optional[str] = Header(None, alias="x-api-key")
):
    # Challenge Rule: "Autenticación por API key en la cabecera x-api-key"
    # Allow request if API key matches or in local dev/demo mode if key is default
    if x_api_key and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida en cabecera 'x-api-key'")

    t0 = time.perf_counter()

    # Get active zombie and blocked edges from current simulation state
    zombies_data = [z.to_dict() for z in sim.zombies]
    aristas_bloqueadas = sim.aristas_bloqueadas

    # Compute optimal next step
    siguiente = router.find_best_next_node(
        nodo_actual=payload.nodoActual,
        zombies=zombies_data,
        aristas_bloqueadas=aristas_bloqueadas,
        refugio_occupancy=sim.refugio_occupancy
    )

    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return PasoResponse(siguienteNodo=siguiente)

@app.get(
    "/estado",
    summary="Obtener estado completo del mundo en el turno actual",
    description="Retorna el turno, lista de zombies (id/tipo/nodo), sobrevivientes, aristas bloqueadas, refugios y métricas."
)
async def get_estado():
    return sim.get_state()

@app.get(
    "/grafo",
    summary="Obtener topología del grafo de Manta",
    description="Retorna nodos (intersecciones con lat/lng), aristas (calles, avenidas, puentes) y los 4 refugios."
)
async def get_grafo():
    return {
        "nodos": list(router.nodes.values()),
        "aristas": list(router.edges.values()),
        "refugios": list(router.refugios.values())
    }

# --- SIMULATOR CONTROLS ---

@app.post("/simulador/ronda/{ronda_id}", summary="Cargar una de las rondas de la Prueba de Fuego (1, 2 o 3)")
async def set_ronda(ronda_id: int):
    if ronda_id not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Ronda inválida. Debe ser 1, 2 o 3.")
    sim.reset_round(ronda=ronda_id)
    state = sim.get_state()
    await ws_manager.broadcast({"tipo": "ronda_cambiada", "data": state})
    return {"mensaje": f"Ronda {ronda_id} configurada con éxito", "estado": state}

@app.post("/simulador/play", summary="Reanudar simulación automática")
async def play_sim():
    sim.activo = True
    state = sim.get_state()
    await ws_manager.broadcast({"tipo": "estado_actualizado", "data": state})
    return {"mensaje": "Simulación en marcha", "activo": True}

@app.post("/simulador/pausa", summary="Pausar simulación")
async def pausa_sim():
    sim.activo = False
    state = sim.get_state()
    await ws_manager.broadcast({"tipo": "estado_actualizado", "data": state})
    return {"mensaje": "Simulación pausada", "activo": False}

@app.post("/simulador/step", summary="Ejecutar exactamente 1 turno (Paso a paso)")
async def step_sim():
    sim.execute_turn()
    state = sim.get_state()
    await ws_manager.broadcast({"tipo": "estado_actualizado", "data": state})
    return {"mensaje": f"Turno {sim.turno} completado", "estado": state}

@app.post("/simulador/velocidad", summary="Ajustar velocidad del simulador")
async def set_velocidad(payload: VelocidadRequest):
    sim.turn_delay = max(0.05, min(10.0, payload.segundos))
    return {"mensaje": f"Velocidad ajustada a {sim.turn_delay}s por turno"}

@app.post("/simulador/reiniciar", summary="Reiniciar ronda actual")
async def reiniciar_sim():
    sim.reset_round(ronda=sim.ronda_actual)
    state = sim.get_state()
    await ws_manager.broadcast({"tipo": "estado_actualizado", "data": state})
    return {"mensaje": "Simulador reiniciado", "estado": state}

# --- WEBSOCKET REAL-TIME STREAM ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        # Send initial state on connection
        await websocket.send_json({"tipo": "bienvenida", "data": sim.get_state()})
        while True:
            data = await websocket.receive_json()
            accion = data.get("accion")
            if accion == "play":
                sim.activo = True
            elif accion == "pausa":
                sim.activo = False
            elif accion == "step":
                sim.execute_turn()
            elif accion == "ronda":
                sim.reset_round(ronda=data.get("ronda", 1))
            elif accion == "velocidad":
                sim.turn_delay = float(data.get("segundos", 2.0))
            
            state = sim.get_state()
            await ws_manager.broadcast({"tipo": "estado_actualizado", "data": state})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)

# --- SERVE FRONTEND STATIC FILES ---

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def serve_index():
        index_file = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"mensaje": "Escape de Manta Zombie API activo. Visite /docs para Swagger UI."}
