"""
Manta City Graph Generator for Spookython 2026 - Track A: Escape de Manta Zombie
Generates a realistic graph of ~300 intersections across Manta's key sectors:
- Tarqui (with Puente Río Manta / Tarqui)
- Los Esteros (coastal & port zone)
- Barbasquillo (south-west coastal zone & ULEAM)
- Jocay (central neighborhood & Estadio Jocay)
- Centro & Malecón Escénico / Playa El Murciélago

Each edge has:
- distancia_m (distance in meters)
- tipo: 'avenida', 'calle', 'callejon', 'puente'
Each node has:
- id: 'N-0001' to 'N-0320'
- name: Real street/intersection names in Manta
- lat, lng: Real coordinates in Manta, Ecuador
- sector: 'Barbasquillo', 'Tarqui', 'Los Esteros', 'Jocay', 'Centro', 'Murcielago'

4 Safe Shelters (Refugios):
- REF-01 (Barbasquillo / ULEAM Campus)
- REF-02 (Los Esteros / Puerto Pesquero)
- REF-03 (Jocay / Estadio Jocay)
- REF-04 (Tarqui / Malecón Escénico)
"""

import json
import math
import random

# Fixed seed for deterministic graph generation
random.seed(404)

SECTORS = {
    "Barbasquillo": {
        "lat_range": (-0.9760, -0.9620),
        "lng_range": (-80.7580, -80.7360),
        "streets": [
            "Vía a Barbasquillo", "Calle 20", "Av. Circunvalación Sur", "Av. 24",
            "Calle 19", "Av. Universitaria", "Calle Barbasquillo", "Av. Flavio Reyes Sur"
        ],
        "node_count": 65
    },
    "Centro": {
        "lat_range": (-0.9560, -0.9460),
        "lng_range": (-80.7320, -80.7150),
        "streets": [
            "Av. 2", "Av. 3", "Av. 4", "Calle 11", "Calle 12", "Calle 13", "Calle 14",
            "Calle 15", "Calle 8", "Av. Malecón Jaime Chávez", "Calle 9", "Calle 10"
        ],
        "node_count": 65
    },
    "Murcielago": {
        "lat_range": (-0.9520, -0.9420),
        "lng_range": (-80.7420, -80.7250),
        "streets": [
            "Av. Flavio Reyes", "Av. 24 de Mayo", "Calle 18", "Calle 17",
            "Malecón Escénico", "Av. de los Turistas", "Calle 16"
        ],
        "node_count": 45
    },
    "Jocay": {
        "lat_range": (-0.9670, -0.9540),
        "lng_range": (-80.7180, -80.7000),
        "streets": [
            "Av. 4 de Noviembre", "Calle J-1", "Calle J-2", "Calle J-3", "Calle J-4",
            "Calle J-7", "Av. Interbarrial", "Av. 113", "Calle J-10", "Calle J-14"
        ],
        "node_count": 65
    },
    "Tarqui": {
        "lat_range": (-0.9600, -0.9480),
        "lng_range": (-80.7050, -80.6880),
        "streets": [
            "Av. 105", "Av. 106", "Av. 107", "Av. 108", "Calle 101", "Calle 102",
            "Calle 103", "Av. 109", "Calle 104", "Calle 105", "Av. de la Cultura"
        ],
        "node_count": 65
    },
    "Los Esteros": {
        "lat_range": (-0.9500, -0.9380),
        "lng_range": (-80.6920, -80.6720),
        "streets": [
            "Av. 101 Los Esteros", "Calle 118", "Calle 119", "Av. 102 Los Esteros",
            "Calle 120", "Av. Puerto Marítimo", "Calle 121", "Vía Interbarrial Norte"
        ],
        "node_count": 55
    }
}

def haversine_m(lat1, lon1, lat2, lon2):
    """Calculates distance in meters between two lat/lng coordinates."""
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)

def generate_manta_graph():
    nodes = []
    node_id_counter = 1
    sector_nodes = {s: [] for s in SECTORS}

    # 1. Generate nodes for each sector
    for sector_name, conf in SECTORS.items():
        min_lat, max_lat = conf["lat_range"]
        min_lng, max_lng = conf["lng_range"]
        streets = conf["streets"]
        
        # Grid-like distribution with organic perturbation
        grid_dim = int(math.ceil(math.sqrt(conf["node_count"])))
        lat_step = (max_lat - min_lat) / (grid_dim + 1)
        lng_step = (max_lng - min_lng) / (grid_dim + 1)
        
        count = 0
        for i in range(1, grid_dim + 1):
            for j in range(1, grid_dim + 1):
                if count >= conf["node_count"]:
                    break
                lat = min_lat + i * lat_step + random.uniform(-lat_step * 0.25, lat_step * 0.25)
                lng = min_lng + j * lng_step + random.uniform(-lng_step * 0.25, lng_step * 0.25)
                street_a = streets[count % len(streets)]
                street_b = streets[(count * 3 + 1) % len(streets)]
                if street_a == street_b:
                    street_b = f"Transversal {count % 15 + 1}"
                
                node_id = f"N-{node_id_counter:04d}"
                node_obj = {
                    "id": node_id,
                    "name": f"{street_a} y {street_b}",
                    "lat": round(lat, 6),
                    "lng": round(lng, 6),
                    "sector": sector_name
                }
                nodes.append(node_obj)
                sector_nodes[sector_name].append(node_obj)
                node_id_counter += 1
                count += 1

    # 2. Assign 4 Designated Refugios (one per strategic quadrant)
    # REF-01: Barbasquillo (ULEAM)
    ref1_node = sector_nodes["Barbasquillo"][10]["id"]
    # REF-02: Los Esteros (Terminal/Puerto)
    ref2_node = sector_nodes["Los Esteros"][12]["id"]
    # REF-03: Jocay (Estadio Jocay)
    ref3_node = sector_nodes["Jocay"][15]["id"]
    # REF-04: Tarqui / Malecón (Tarqui Seguro)
    ref4_node = sector_nodes["Tarqui"][18]["id"]

    refugios = [
        {
            "id": "REF-01",
            "name": "Refugio ULEAM - Barbasquillo",
            "nodo": ref1_node,
            "capacidad_max": 75,
            "sector": "Barbasquillo",
            "descripcion": "Zona alta protegida en campus universitario ULEAM."
        },
        {
            "id": "REF-02",
            "name": "Refugio Puerto Pesquero - Los Esteros",
            "nodo": ref2_node,
            "capacidad_max": 75,
            "sector": "Los Esteros",
            "descripcion": "Instalación portuaria amurallada en Los Esteros."
        },
        {
            "id": "REF-03",
            "name": "Refugio Estadio Jocay",
            "nodo": ref3_node,
            "capacidad_max": 75,
            "sector": "Jocay",
            "descripcion": "Complejo deportivo con perímetro fortificado."
        },
        {
            "id": "REF-04",
            "name": "Refugio Malecón Escénico - Tarqui",
            "nodo": ref4_node,
            "capacidad_max": 75,
            "sector": "Tarqui",
            "descripcion": "Base naval de emergencia en el malecón de Tarqui."
        }
    ]

    # Mark refuge nodes in node list
    ref_map = {r["nodo"]: r["id"] for r in refugios}
    for n in nodes:
        if n["id"] in ref_map:
            n["is_refugio"] = True
            n["refugio_id"] = ref_map[n["id"]]
        else:
            n["is_refugio"] = False

    # 3. Create realistic street edges
    # Connect nearest neighbors inside sectors, and inter-sector arterials
    edges = []
    edge_set = set()

    def add_edge(u_id, v_id, street_type=None, name=None):
        if u_id == v_id:
            return
        pair = tuple(sorted([u_id, v_id]))
        if pair in edge_set:
            return
        edge_set.add(pair)

        u = next(x for x in nodes if x["id"] == u_id)
        v = next(x for x in nodes if x["id"] == v_id)
        dist = haversine_m(u["lat"], u["lng"], v["lat"], v["lng"])

        if street_type is None:
            # Determine street type based on distance and names
            if dist > 380:
                street_type = "avenida"
            elif dist < 120:
                street_type = "callejon"
            else:
                street_type = "calle"

        # Edge speeds (km/h & relative weight factors):
        # avenida: 50 km/h (speed factor 1.25)
        # calle: 30 km/h (speed factor 1.0)
        # callejon: 15 km/h (speed factor 0.7)
        # puente: 40 km/h (speed factor 1.1)
        speed_factors = {
            "avenida": 1.25,
            "calle": 1.00,
            "callejon": 0.70,
            "puente": 1.10
        }

        edge_data = {
            "id": f"E-{len(edges)+1:04d}",
            "origen": u_id,
            "destino": v_id,
            "nombre": name or f"Conexión {u['name'].split(' y ')[0]}",
            "distancia_m": dist,
            "tipo": street_type,
            "velocidad_factor": speed_factors[street_type],
            "peso_tiempo": round(dist / speed_factors[street_type], 2)
        }
        edges.append(edge_data)

    # Connect internal sector nodes (k-nearest neighbors)
    for sector_name, s_nodes in sector_nodes.items():
        for i, u in enumerate(s_nodes):
            # Sort all other nodes in same sector by distance
            neighbors = sorted(
                [v for j, v in enumerate(s_nodes) if i != j],
                key=lambda v: haversine_m(u["lat"], u["lng"], v["lat"], v["lng"])
            )
            # Connect to 3-4 closest neighbors to ensure high connectivity and alternate routes
            for v in neighbors[:3]:
                add_edge(u["id"], v["id"])
            if random.random() < 0.4 and len(neighbors) > 3:
                add_edge(u["id"], neighbors[3]["id"])

    # Inter-sector Arterials & Bridges
    # Connect Barbasquillo <-> Centro & Murciélago (Av. Flavio Reyes / Av. Circunvalación)
    for u in sector_nodes["Barbasquillo"][-10:]:
        closest = min(sector_nodes["Centro"], key=lambda v: haversine_m(u["lat"], u["lng"], v["lat"], v["lng"]))
        add_edge(u["id"], closest["id"], "avenida", "Av. Circunvalación Sur - Flavio Reyes")

    for u in sector_nodes["Murcielago"][:8]:
        closest = min(sector_nodes["Centro"], key=lambda v: haversine_m(u["lat"], u["lng"], v["lat"], v["lng"]))
        add_edge(u["id"], closest["id"], "avenida", "Av. Malecón Jaime Chávez Gutiérrez")

    # Connect Centro <-> Jocay (Av. 4 de Noviembre / Calle 13)
    for u in sector_nodes["Centro"][-10:]:
        closest = min(sector_nodes["Jocay"], key=lambda v: haversine_m(u["lat"], u["lng"], v["lat"], v["lng"]))
        add_edge(u["id"], closest["id"], "avenida", "Av. 4 de Noviembre")

    # Connect Jocay <-> Tarqui (Av. 113 / Av. de la Cultura)
    for u in sector_nodes["Jocay"][-10:]:
        closest = min(sector_nodes["Tarqui"], key=lambda v: haversine_m(u["lat"], u["lng"], v["lat"], v["lng"]))
        add_edge(u["id"], closest["id"], "avenida", "Av. de la Cultura")

    # Bridges connecting Tarqui <-> Los Esteros over Río Manta!
    # These are critical bridges that can collapse as City Events in Ronda 2 & 3
    tarqui_border = sorted(sector_nodes["Tarqui"], key=lambda x: x["lng"], reverse=True)[:6]
    esteros_border = sorted(sector_nodes["Los Esteros"], key=lambda x: x["lng"])[:6]
    
    # Puente Principal de Tarqui (Bridge 1)
    add_edge(tarqui_border[0]["id"], esteros_border[0]["id"], "puente", "Puente Principal Río Tarqui")
    # Puente Secundario Malecón (Bridge 2)
    add_edge(tarqui_border[1]["id"], esteros_border[1]["id"], "puente", "Puente Interbarrial Tarqui-Los Esteros")
    # Puente Pasarela Comercial (Bridge 3)
    add_edge(tarqui_border[2]["id"], esteros_border[2]["id"], "puente", "Puente Mercado del Marisco")

    # Additional connections between Tarqui and Los Esteros
    add_edge(tarqui_border[3]["id"], esteros_border[3]["id"], "calle", "Vía de Enlace Portuario")

    graph_data = {
        "ciudad": "Manta, Ecuador",
        "total_nodos": len(nodes),
        "total_aristas": len(edges),
        "refugios": refugios,
        "nodos": nodes,
        "aristas": edges
    }

    return graph_data

if __name__ == "__main__":
    data = generate_manta_graph()
    print(f"Graph generated: {data['total_nodos']} nodes, {data['total_aristas']} edges, {len(data['refugios'])} refugios.")
    with open("manta_graph.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("Saved to manta_graph.json")
