"""
Apocalypse Simulator for Spookython 2026 - Track A: Escape de Manta Zombie

Runs the simulation loop, moves zombies according to rules, triggers city events,
queries the routing engine via POST /paso, handles bites/rescues, and tracks live metrics.
"""

import time
import random
import statistics
from typing import List, Dict, Set, Optional, Any, Callable
from src.config import FIRE_TEST_ROUNDS, DEFAULT_TURN_SECONDS, FAST_TURN_SECONDS
from src.simulator.entities import ZombieEntity, SobrevivienteEntity, CamionetaRescateEntity
from src.engine.router import MantaRouter

class ApocalypseSimulator:
    def __init__(self, router: MantaRouter, paso_handler: Optional[Callable] = None):
        self.router = router
        self.paso_handler = paso_handler  # Function to query /paso (can be internal or HTTP)
        
        # State
        self.turno: int = 0
        self.ronda_actual: int = 1
        self.activo: bool = False
        self.turn_delay: float = DEFAULT_TURN_SECONDS
        
        # Entities
        self.zombies: List[ZombieEntity] = []
        self.sobrevivientes: List[SobrevivienteEntity] = []
        self.camionetas: List[CamionetaRescateEntity] = []
        self.aristas_bloqueadas: Set[str] = set()
        self.eventos_historial: List[Dict[str, Any]] = []
        self.latencias_paso_ms: List[float] = []
        self.refugio_occupancy: Dict[str, int] = {r_id: 0 for r_id in self.router.refugios}
        self.flota_rescate_activa: bool = True

    def reset_round(self, ronda: int = 1):
        """Initializes a new round matching the Fire Test specifications."""
        self.ronda_actual = ronda
        self.turno = 0
        self.activo = False
        self.latencias_paso_ms.clear()
        self.aristas_bloqueadas.clear()
        self.eventos_historial.clear()
        self.refugio_occupancy = {r_id: 0 for r_id in self.router.refugios}
        
        conf = FIRE_TEST_ROUNDS.get(ronda, FIRE_TEST_ROUNDS[1])
        all_node_ids = list(self.router.nodes.keys())
        refuge_node_ids = {r["nodo"] for r in self.router.refugios.values()}
        available_nodes = [nid for nid in all_node_ids if nid not in refuge_node_ids]

        # 1. Spawn Survivors in designated sectors (Tarqui, Los Esteros, Barbasquillo, Jocay)
        self.sobrevivientes = []
        num_survivors = conf["sobrevivientes_iniciales"]
        
        # Group non-refuge nodes by sector
        sector_nodes: Dict[str, List[str]] = {}
        for nid in available_nodes:
            sec = self.router.nodes[nid].get("sector", "Centro")
            sector_nodes.setdefault(sec, []).append(nid)

        spawn_sectors = ["Tarqui", "Los Esteros", "Barbasquillo", "Jocay"]
        for i in range(num_survivors):
            target_sec = spawn_sectors[i % len(spawn_sectors)]
            pool = sector_nodes.get(target_sec, available_nodes)
            spawn_node = random.choice(pool)
            
            s = SobrevivienteEntity(
                id=f"S-{i+1:04d}",
                nodo=spawn_node,
                nodo_anterior=None,
                estado="vivo"
            )
            # Compute baseline shortest path without zombies for efficiency metric
            _, path = self.router.dijkstra_to_refuges(
                start_node=spawn_node,
                target_refuges=[(r["id"], r["nodo"], 0.0) for r in self.router.refugios.values()],
                aristas_bloqueadas=set(),
                danger_penalties={nid: 0.0 for nid in self.router.nodes},
                lethal_nodes=set()
            )
            s.distancia_optima_inicial = max(1, len(path) - 1)
            s.ruta_planificada = path
            self.sobrevivientes.append(s)

        # 2. Spawn Zombies according to round specifications
        self.zombies = []
        z_counter = 1
        z_conf = conf["zombies"]
        
        for z_type, count in z_conf.items():
            for _ in range(count):
                spawn_node = random.choice(available_nodes)
                self.zombies.append(ZombieEntity(
                    id=f"Z-{z_counter:03d}",
                    tipo=z_type,
                    nodo=spawn_node,
                    despierto=(z_type != "dormido"),
                    contador_turnos=0
                ))
                z_counter += 1

        # 3. Spawn 5 Rescue Vans (Nivel PRO: Flota de Rescate)
        self.camionetas = []
        refuge_list = list(self.router.refugios.values())
        for v_idx in range(5):
            ref = refuge_list[v_idx % len(refuge_list)]
            self.camionetas.append(CamionetaRescateEntity(
                id=f"CAM-{v_idx+1}",
                nodo=ref["nodo"],
                capacidad_max=4,
                refugio_base=ref["id"],
                estado="patrullando"
            ))

        self.emit_event("sistema", f"Ronda {ronda} iniciada: '{conf['nombre']}'. {num_survivors} sobrevivientes, {len(self.zombies)} zombies.")

    def emit_event(self, tipo: str, descripcion: str, extra: Optional[Dict[str, Any]] = None):
        ev = {
            "turno": self.turno,
            "tiempo": time.strftime("%H:%M:%S"),
            "tipo": tipo,
            "descripcion": descripcion,
            "extra": extra or {}
        }
        self.eventos_historial.append(ev)
        # Keep last 50 events for memory
        if len(self.eventos_historial) > 50:
            self.eventos_historial.pop(0)

    def execute_turn(self):
        """Executes one full simulation turn of 2 seconds."""
        self.turno += 1

        # PHASE 1: MOVE ZOMBIES
        self._move_zombies()

        # PHASE 2: TRIGGER CITY EVENTS (Bridge collapses, blocked streets)
        self._check_city_events()

        # PHASE 3: SURVIVORS QUERY /paso AND MOVE
        self._move_survivors()

        # PHASE 4: RESCUE VANS (Nivel PRO)
        if self.flota_rescate_activa:
            self._move_rescue_vans()

        # PHASE 5: EVALUATE RESCUES AND BITES
        self._evaluate_bites_and_rescues()

    def _move_zombies(self):
        alive_survivor_nodes = {s.nodo for s in self.sobrevivientes if s.estado == "vivo"}

        for z in self.zombies:
            z.contador_turnos += 1
            z.nodo_anterior = z.nodo

            # Check dormant zombies awakening condition:
            # "Dormido: invisible hasta que un sobreviviente está a 2 nodos o menos; ahí despierta"
            if z.tipo == "dormido":
                if not z.despierto:
                    for snode in alive_survivor_nodes:
                        if self.router.get_hop_distance(z.nodo, snode, max_hops=2) <= 2:
                            z.despierto = True
                            self.emit_event(
                                "zombie_despierto",
                                f"¡ZOMBIE DORMIDO ({z.id}) HA DESPERTADO en {z.nodo}! Se convierte en caminante."
                            )
                            break
                if not z.despierto:
                    continue  # Remains asleep and stationary

            # Caminante:
            # "1 calle cada 2 turnos, dirección aleatoria"
            if z.tipo in ("caminante", "dormido"):
                if z.contador_turnos % 2 == 0:
                    valid_moves = [
                        e["neighbor"] for e in self.router.adj.get(z.nodo, [])
                        if e["edge_id"] not in self.aristas_bloqueadas
                    ]
                    if valid_moves:
                        z.nodo = random.choice(valid_moves)

            # Corredor:
            # "2 calles por turno; persigue si hay un sobreviviente a 3 nodos o menos"
            elif z.tipo == "corredor":
                for _ in range(2):  # Moves up to 2 streets per turn
                    valid_moves = [
                        e["neighbor"] for e in self.router.adj.get(z.nodo, [])
                        if e["edge_id"] not in self.aristas_bloqueadas
                    ]
                    if not valid_moves:
                        break

                    # Check for survivor within 3 hops
                    closest_survivor_node = None
                    min_hops = 999
                    for snode in alive_survivor_nodes:
                        h = self.router.get_hop_distance(z.nodo, snode, max_hops=3)
                        if h < min_hops:
                            min_hops = h
                            closest_survivor_node = snode

                    if closest_survivor_node and min_hops <= 3:
                        # Pursue closest survivor! Choose neighbor that minimizes hop distance
                        best_move = min(
                            valid_moves,
                            key=lambda nbr: self.router.get_hop_distance(nbr, closest_survivor_node, max_hops=4)
                        )
                        z.nodo = best_move
                    else:
                        # Patrols randomly
                        z.nodo = random.choice(valid_moves)

            # Horda:
            # "Casi inmóvil, bloquea su nodo y todos los vecinos"
            elif z.tipo == "horda":
                # 95% immobile, 5% random slow crawl
                if random.random() < 0.05:
                    valid_moves = [
                        e["neighbor"] for e in self.router.adj.get(z.nodo, [])
                        if e["edge_id"] not in self.aristas_bloqueadas
                    ]
                    if valid_moves:
                        z.nodo = random.choice(valid_moves)

    def _check_city_events(self):
        conf = FIRE_TEST_ROUNDS.get(self.ronda_actual, {})
        for event in conf.get("eventos", []):
            if event["turno"] == self.turno:
                edge_name = event.get("arista_nombre", "")
                # Find matching edge in graph
                target_edge_id = None
                for eid, edata in self.router.edges.items():
                    if edge_name.lower() in edata["nombre"].lower():
                        target_edge_id = eid
                        break

                if target_edge_id and target_edge_id not in self.aristas_bloqueadas:
                    self.aristas_bloqueadas.add(target_edge_id)
                    self.emit_event(
                        "evento_ciudad",
                        f"🚨 {event['descripcion']}",
                        {"arista_id": target_edge_id, "nombre": edge_name}
                    )

    def _move_survivors(self):
        zombie_dicts = [z.to_dict() for z in self.zombies]

        for s in self.sobrevivientes:
            if s.estado != "vivo":
                continue

            # Query POST /paso and measure latency
            t0 = time.perf_counter()
            siguiente_nodo = self._call_paso(s.id, s.nodo, self.turno, zombie_dicts)
            dt_ms = (time.perf_counter() - t0) * 1000.0
            self.latencias_paso_ms.append(dt_ms)

            # Enforce 500ms timeout rule:
            # "DEBE responder en menos de 500 ms; si no, el sobreviviente se queda quieto ese turno."
            if dt_ms > 500.0:
                siguiente_nodo = s.nodo

            # Validate next node:
            # "siguienteNodo DEBE ser vecino por una calle no bloqueada, o el mismo nodo."
            valid_neighbors = {
                e["neighbor"] for e in self.router.adj.get(s.nodo, [])
                if e["edge_id"] not in self.aristas_bloqueadas
            }
            valid_neighbors.add(s.nodo)

            if siguiente_nodo not in valid_neighbors:
                siguiente_nodo = s.nodo  # Invalid move defaults to staying put

            s.nodo_anterior = s.nodo
            s.nodo = siguiente_nodo
            s.turnos_viajados += 1

            # Update planned path for live UI visualization
            s.ruta_planificada = self.router.get_full_path_to_shelter(
                s.nodo,
                zombie_dicts,
                self.aristas_bloqueadas
            )

    def _call_paso(self, sobreviviente_id: str, nodo_actual: str, turno: int, zombies: List[Dict[str, Any]]) -> str:
        """Invokes the route engine logic."""
        if self.paso_handler:
            return self.paso_handler(sobreviviente_id, nodo_actual, turno, zombies, self.aristas_bloqueadas, self.refugio_occupancy)
        # Default internal call
        return self.router.find_best_next_node(
            nodo_actual=nodo_actual,
            zombies=zombies,
            aristas_bloqueadas=self.aristas_bloqueadas,
            refugio_occupancy=self.refugio_occupancy
        )

    def _move_rescue_vans(self):
        """Nivel PRO: 5 vans move at 2x speed, pick up survivors, bring to shelter"""
        refuge_nodes = {r["nodo"]: r["id"] for r in self.router.refugios.values()}

        for van in self.camionetas:
            # 1. If at shelter with passengers, deposit them!
            if van.nodo in refuge_nodes and van.pasajeros:
                ref_id = refuge_nodes[van.nodo]
                for s_id in van.pasajeros:
                    s = next((x for x in self.sobrevivientes if x.id == s_id), None)
                    if s and s.estado == "en_camioneta":
                        s.estado = "rescatado"
                        s.refugio_alcanzado = ref_id
                        self.refugio_occupancy[ref_id] = self.refugio_occupancy.get(ref_id, 0) + 1
                van.pasajeros.clear()
                van.estado = "patrullando"

            # 2. Pick up alive survivors at current van node
            if len(van.pasajeros) < van.capacidad_max:
                for s in self.sobrevivientes:
                    if s.estado == "vivo" and s.nodo == van.nodo:
                        s.estado = "en_camioneta"
                        s.camioneta_id = van.id
                        van.pasajeros.append(s.id)
                        if len(van.pasajeros) >= van.capacidad_max:
                            van.estado = "rumbo_refugio"
                            break

            # 3. Move van (vans move 2 hops per turn)
            for _ in range(2):
                if van.estado == "rumbo_refugio" or len(van.pasajeros) >= 2:
                    # Head toward nearest shelter
                    target_refuges = [(r["id"], r["nodo"], 0.0) for r in self.router.refugios.values()]
                    _, path = self.router.dijkstra_to_refuges(
                        van.nodo, target_refuges, self.aristas_bloqueadas,
                        {nid: 0.0 for nid in self.router.nodes}, set()
                    )
                    if len(path) > 1:
                        van.nodo = path[1]
                else:
                    # Patrol towards closest alive survivor
                    alive_survivors = [s for s in self.sobrevivientes if s.estado == "vivo"]
                    if alive_survivors:
                        closest_s = min(
                            alive_survivors,
                            key=lambda s: self.router.get_hop_distance(van.nodo, s.nodo, max_hops=6)
                        )
                        valid_moves = [
                            e["neighbor"] for e in self.router.adj.get(van.nodo, [])
                            if e["edge_id"] not in self.aristas_bloqueadas
                        ]
                        if valid_moves:
                            best_van_step = min(
                                valid_moves,
                                key=lambda nbr: self.router.get_hop_distance(nbr, closest_s.nodo, max_hops=6)
                            )
                            van.nodo = best_van_step
                
                # Check for pickup along the way
                if len(van.pasajeros) < van.capacidad_max:
                    for s in self.sobrevivientes:
                        if s.estado == "vivo" and s.nodo == van.nodo:
                            s.estado = "en_camioneta"
                            s.camioneta_id = van.id
                            van.pasajeros.append(s.id)

    def _evaluate_bites_and_rescues(self):
        refuge_nodes = {r["nodo"]: r["id"] for r in self.router.refugios.values()}

        # Identify horde nodes and their neighbors
        horde_lethal_nodes = set()
        for z in self.zombies:
            if z.tipo == "horda":
                horde_lethal_nodes.add(z.nodo)
                for edge in self.router.adj.get(z.nodo, []):
                    horde_lethal_nodes.add(edge["neighbor"])

        for s in self.sobrevivientes:
            if s.estado != "vivo":
                continue

            # 1. CHECK MORDIDAS (Bites)
            mordido = False
            causa = ""

            # Rule A: Shares node with active zombie at the end of turn
            for z in self.zombies:
                if z.tipo != "dormido" and z.nodo == s.nodo:
                    mordido = True
                    causa = f"compartió nodo con zombie {z.tipo} ({z.id})"
                    break

            # Rule B: Crossed paths on the same street in opposite directions
            if not mordido:
                for z in self.zombies:
                    if z.tipo != "dormido" and s.nodo_anterior == z.nodo and s.nodo == z.nodo_anterior:
                        mordido = True
                        causa = f"cruce frontal en misma calle con {z.tipo} ({z.id})"
                        break

            # Rule C: Horde lethal zone (horde node or any horde neighbor)
            if not mordido and s.nodo in horde_lethal_nodes:
                mordido = True
                causa = "atrapado en zona de influencia de horda"

            if mordido:
                s.estado = "mordido"
                self.emit_event(
                    "baja",
                    f"💀 Sobreviviente {s.id} mordido en {s.nodo}: {causa}."
                )
                continue

            # 2. CHECK RESCUE
            if s.nodo in refuge_nodes:
                ref_id = refuge_nodes[s.nodo]
                s.estado = "rescatado"
                s.refugio_alcanzado = ref_id
                self.refugio_occupancy[ref_id] = self.refugio_occupancy.get(ref_id, 0) + 1
                self.emit_event(
                    "rescate",
                    f"🛡️ ¡Sobreviviente {s.id} ha llegado al {self.router.refugios[ref_id]['name']}!"
                )

    def get_state(self) -> Dict[str, Any]:
        """Returns the complete world state for GET /estado or WebSocket push."""
        total = len(self.sobrevivientes)
        vivos = sum(1 for s in self.sobrevivientes if s.estado in ("vivo", "en_camioneta"))
        rescatados = sum(1 for s in self.sobrevivientes if s.estado == "rescatado")
        mordidos = sum(1 for s in self.sobrevivientes if s.estado == "mordido")

        pct_supervivencia = round((rescatados / max(1, total)) * 100, 1)

        # Latency statistics
        if self.latencias_paso_ms:
            sorted_lat = sorted(self.latencias_paso_ms)
            p50 = round(statistics.median(sorted_lat), 2)
            p95_idx = int(0.95 * len(sorted_lat))
            p95 = round(sorted_lat[min(p95_idx, len(sorted_lat)-1)], 2)
            p99_idx = int(0.99 * len(sorted_lat))
            p99 = round(sorted_lat[min(p99_idx, len(sorted_lat)-1)], 2)
            max_lat = round(sorted_lat[-1], 2)
        else:
            p50 = p95 = p99 = max_lat = 0.0

        # Efficiency calculation
        finished = [s for s in self.sobrevivientes if s.estado == "rescatado"]
        if finished:
            avg_eff = round(sum(s.distancia_optima_inicial / max(1, s.turnos_viajados) for s in finished) / len(finished) * 100, 1)
        else:
            avg_eff = 100.0

        return {
            "turno": self.turno,
            "ronda": self.ronda_actual,
            "activo": self.activo,
            "turn_delay": self.turn_delay,
            "aristas_bloqueadas": list(self.aristas_bloqueadas),
            "zombies": [z.to_dict() for z in self.zombies],
            "sobrevivientes": [s.to_dict() for s in self.sobrevivientes],
            "camionetas": [c.to_dict() for c in self.camionetas],
            "refugios": [
                {
                    **r,
                    "ocupacion": self.refugio_occupancy.get(r["id"], 0)
                } for r in self.router.refugios.values()
            ],
            "eventos": self.eventos_historial[-15:],
            "stats": {
                "total": total,
                "vivos": vivos,
                "rescatados": rescatados,
                "mordidos": mordidos,
                "supervivencia_pct": pct_supervivencia,
                "latencia_p50_ms": p50,
                "latencia_p95_ms": p95,
                "latencia_p99_ms": p99,
                "latencia_max_ms": max_lat,
                "eficiencia_pct": min(100.0, avg_eff),
                "disponibilidad_pct": 100.0
            }
        }
