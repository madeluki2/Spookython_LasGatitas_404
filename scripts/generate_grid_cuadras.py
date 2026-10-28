"""
Manta City Grid Generator - Google Maps Style (Manhattan Block by Block / Cuadras)
Generates an orthogonal, realistic city street grid across Manta:
- Tarqui, Los Esteros, Barbasquillo, Jocay, Centro, El Murciélago
- Strict block-by-block street connectivity (Horizontal Calles + Vertical Avenidas)
- NO random diagonal criss-crossing
- Realistic block distances (~90m - 140m per cuadra)
- Real street and avenue names for Manta
- 4 Strategic Refugios
"""

import json
import math

SECTOR_CONFIGS = {
    "Barbasquillo": {
        "lat_start": -0.9630, "lat_step": -0.0011, "rows": 8,
        "lng_start": -80.7500, "lng_step": 0.0012, "cols": 8,
        "calles": ["Calle Barbasquillo", "Calle 19", "Calle 20", "Calle 21", "Calle 22", "Calle 23", "Calle 24", "Calle 25"],
        "avenidas": ["Vía a Barbasquillo", "Av. Circunvalación Sur", "Av. Universitaria", "Av. 24", "Av. 26", "Av. 28", "Av. 30", "Av. 32"]
    },
    "Centro": {
        "lat_start": -0.9470, "lat_step": -0.0010, "rows": 7,
        "lng_start": -80.7300, "lng_step": 0.0012, "cols": 8,
        "calles": ["Av. Malecón Jaime Chávez", "Calle 8", "Calle 9", "Calle 10", "Calle 11", "Calle 12", "Calle 13"],
        "avenidas": ["Av. 1", "Av. 2", "Av. 3", "Av. 4", "Av. 5", "Av. 6", "Av. 7", "Av. 8"]
    },
    "Murcielago": {
        "lat_start": -0.9450, "lat_step": -0.0010, "rows": 6,
        "lng_start": -80.7420, "lng_step": 0.0012, "cols": 7,
        "calles": ["Malecón Escénico", "Calle 15", "Calle 16", "Calle 17", "Calle 18", "Calle 19"],
        "avenidas": ["Av. Flavio Reyes", "Av. 24 de Mayo", "Av. San Mateo", "Av. del Ejército", "Av. La Bahía", "Av. de los Turistas", "Av. Las Acacias"]
    },
    "Jocay": {
        "lat_start": -0.9550, "lat_step": -0.0011, "rows": 8,
        "lng_start": -80.7180, "lng_step": 0.0012, "cols": 8,
        "calles": ["Calle J-1", "Calle J-2", "Calle J-3", "Calle J-4", "Calle J-6", "Calle J-8", "Calle J-10", "Calle J-12"],
        "avenidas": ["Av. 4 de Noviembre", "Av. 113", "Av. Interbarrial", "Av. J-5", "Av. J-7", "Av. J-9", "Av. J-11", "Av. J-14"]
    },
    "Tarqui": {
        "lat_start": -0.9500, "lat_step": -0.0010, "rows": 8,
        "lng_start": -80.7040, "lng_step": 0.0012, "cols": 8,
        "calles": ["Calle 101", "Calle 102", "Calle 103", "Calle 104", "Calle 105", "Calle 106", "Calle 107", "Calle 108"],
        "avenidas": ["Av. de la Cultura", "Av. 105", "Av. 106", "Av. 107", "Av. 108", "Av. 109", "Av. 110", "Av. 111"]
    },
    "Los Esteros": {
        "lat_start": -0.9400, "lat_step": -0.0010, "rows": 7,
        "lng_start": -80.6900, "lng_step": 0.0012, "cols": 7,
        "calles": ["Calle 116", "Calle 117", "Calle 118", "Calle 119", "Calle 120", "Calle 121", "Calle 122"],
        "avenidas": ["Av. 101 Los Esteros", "Av. 102 Los Esteros", "Av. Puerto Marítimo", "Av. Pesquera", "Av. Interbarrial Norte", "Av. 103", "Av. 104"]
    }
}

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)

def generate_google_maps_style_graph():
    nodes = []
    edges = []
    edge_set = set()
    node_id_counter = 1
    edge_id_counter = 1

    sector_grid = {}

    # 1. Create grid nodes (cuadras / intersections)
    for sec_name, conf in SECTOR_CONFIGS.items():
        sector_grid[sec_name] = []
        rows = conf["rows"]
        cols = conf["cols"]
        for r in range(rows):
            row_nodes = []
            calle_name = conf["calles"][r % len(conf["calles"])]
            for c in range(cols):
                av_name = conf["avenidas"][c % len(conf["avenidas"])]
                lat = round(conf["lat_start"] + r * conf["lat_step"], 6)
                lng = round(conf["lng_start"] + c * conf["lng_step"], 6)
                nid = f"N-{node_id_counter:04d}"
                node_obj = {
                    "id": nid,
                    "name": f"{calle_name} y {av_name}",
                    "lat": lat,
                    "lng": lng,
                    "sector": sec_name,
                    "row": r,
                    "col": c
                }
                nodes.append(node_obj)
                row_nodes.append(node_obj)
                node_id_counter += 1
            sector_grid[sec_name].append(row_nodes)

    def add_edge(u_id, v_id, street_type="calle", name=None):
        nonlocal edge_id_counter
        if u_id == v_id:
            return
        pair = tuple(sorted([u_id, v_id]))
        if pair in edge_set:
            return
        edge_set.add(pair)

        u = next(x for x in nodes if x["id"] == u_id)
        v = next(x for x in nodes if x["id"] == v_id)
        dist = haversine_m(u["lat"], u["lng"], v["lat"], v["lng"])

        speed_factors = {
            "avenida": 1.25,
            "calle": 1.00,
            "callejon": 0.70,
            "puente": 1.10
        }

        edge_data = {
            "id": f"E-{edge_id_counter:04d}",
            "origen": u_id,
            "destino": v_id,
            "nombre": name or f"Tramo {u['name'].split(' y ')[0]}",
            "distancia_m": dist,
            "tipo": street_type,
            "velocidad_factor": speed_factors[street_type],
            "peso_tiempo": round(dist / speed_factors[street_type], 2)
        }
        edges.append(edge_data)
        edge_id_counter += 1

    # 2. Connect block-by-block streets (Orthogonal Cuadras)
    for sec_name, grid in sector_grid.items():
        rows = len(grid)
        cols = len(grid[0])

        for r in range(rows):
            for c in range(cols):
                curr = grid[r][c]
                # Horizontal street connection (East-West)
                if c + 1 < cols:
                    right = grid[r][c + 1]
                    add_edge(curr["id"], right["id"], "calle", f"{curr['name'].split(' y ')[0]}")
                # Vertical avenue connection (North-South)
                if r + 1 < rows:
                    down = grid[r + 1][c]
                    add_edge(curr["id"], down["id"], "avenida", f"{curr['name'].split(' y ')[1]}")

    # 3. Inter-sector connecting Arterials (Avenidas principales de Manta)
    # Barbasquillo <-> Centro / Murciélago (Av. Flavio Reyes / Av. Circunvalación Sur)
    for c in range(4):
        u = sector_grid["Barbasquillo"][0][c * 2]  # North edge of Barbasquillo
        v = sector_grid["Murcielago"][-1][c * 2]   # South edge of Murcielago
        add_edge(u["id"], v["id"], "avenida", "Av. Flavio Reyes - Conexión Costera")

    # Centro <-> Murciélago (Av. Malecón Jaime Chávez Gutiérrez)
    for r in range(5):
        u = sector_grid["Murcielago"][r][-1]  # East edge of Murcielago
        v = sector_grid["Centro"][r][0]       # West edge of Centro
        add_edge(u["id"], v["id"], "avenida", "Av. Malecón Jaime Chávez Gutiérrez")

    # Centro <-> Jocay (Av. 4 de Noviembre / Calle 13)
    for c in range(4):
        u = sector_grid["Centro"][-1][c * 2]  # South edge of Centro
        v = sector_grid["Jocay"][0][c * 2]    # North edge of Jocay
        add_edge(u["id"], v["id"], "avenida", "Av. 4 de Noviembre")

    # Jocay <-> Tarqui (Av. 113 / Av. de la Cultura)
    for r in range(5):
        u = sector_grid["Jocay"][r][-1]  # East edge of Jocay
        v = sector_grid["Tarqui"][r][0]  # West edge of Tarqui
        add_edge(u["id"], v["id"], "avenida", "Av. de la Cultura")

    # Tarqui <-> Los Esteros (Puentes sobre el Río Manta / Río Tarqui)
    # Puente 1: Puente Principal Río Tarqui (Collapses in Ronda 2!)
    u_bridge1 = sector_grid["Tarqui"][0][2]
    v_bridge1 = sector_grid["Los Esteros"][-1][2]
    add_edge(u_bridge1["id"], v_bridge1["id"], "puente", "Puente Principal Río Tarqui")

    # Puente 2: Puente Interbarrial Tarqui-Los Esteros
    u_bridge2 = sector_grid["Tarqui"][0][4]
    v_bridge2 = sector_grid["Los Esteros"][-1][4]
    add_edge(u_bridge2["id"], v_bridge2["id"], "puente", "Puente Interbarrial Tarqui-Los Esteros")

    # Puente 3: Puente Mercado del Marisco
    u_bridge3 = sector_grid["Tarqui"][0][6]
    v_bridge3 = sector_grid["Los Esteros"][-1][6]
    add_edge(u_bridge3["id"], v_bridge3["id"], "puente", "Puente Mercado del Marisco")

    # 4. Strategic Refugios
    ref1_node = sector_grid["Barbasquillo"][4][3]["id"]
    ref2_node = sector_grid["Los Esteros"][2][3]["id"]
    ref3_node = sector_grid["Jocay"][4][4]["id"]
    ref4_node = sector_grid["Tarqui"][4][3]["id"]

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

    ref_map = {r["nodo"]: r["id"] for r in refugios}
    for n in nodes:
        n["is_refugio"] = (n["id"] in ref_map)
        n["refugio_id"] = ref_map.get(n["id"])

    return {
        "ciudad": "Manta, Ecuador",
        "total_nodos": len(nodes),
        "total_aristas": len(edges),
        "refugios": refugios,
        "nodos": nodes,
        "aristas": edges
    }

if __name__ == "__main__":
    data = generate_google_maps_style_graph()
    print(f"Cuadras Grid Generated: {data['total_nodos']} nodes, {data['total_aristas']} edges, {len(data['refugios'])} refugios.")
    with open("manta_graph.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    with open("src/data/manta_graph.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("Saved to manta_graph.json and src/data/manta_graph.json")
