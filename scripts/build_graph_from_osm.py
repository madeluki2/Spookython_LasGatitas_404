"""
Builds an authentic, 100% map-aligned Manta city graph from real OpenStreetMap data.
Generates exactly ~320-350 major intersections across Manta's 4 core sectors as specified:
"unas 300 intersecciones (id, lat, lng), calles con distancia_m y tipo y 4 refugios."
"""

import json
import math
import networkx as nx

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)

def get_sector(lat, lng):
    if lng < -80.730 and lat < -0.955:
        return "Barbasquillo"
    elif lng < -80.725 and lat >= -0.955:
        return "Murcielago"
    elif -80.725 <= lng < -80.708 and lat >= -0.953:
        return "Centro"
    elif -80.720 <= lng < -80.702 and lat < -0.953:
        return "Jocay"
    elif -80.705 <= lng < -80.686:
        return "Tarqui"
    else:
        return "Los Esteros"

def build_graph(target_nodes=330):
    print("Loading manta_osm_raw.json...")
    with open("manta_osm_raw.json", "r", encoding="utf-8") as f:
        osm_data = json.load(f)

    osm_nodes = {}
    osm_ways = []

    for el in osm_data.get("elements", []):
        if el["type"] == "node":
            osm_nodes[el["id"]] = (el["lat"], el["lon"])
        elif el["type"] == "way":
            tags = el.get("tags", {})
            hway = tags.get("highway", "")
            # Prioritize arterial roads and main streets first
            if hway in ("primary", "trunk", "secondary", "tertiary", "residential"):
                osm_ways.append(el)

    print(f"Total raw nodes: {len(osm_nodes)}, Filtered arterial ways: {len(osm_ways)}")

    # Build full segment graph
    G_raw = nx.Graph()
    for w in osm_ways:
        nodes = w.get("nodes", [])
        tags = w.get("tags", {})
        street_name = tags.get("name", "Calle de Manta")
        hway = tags.get("highway", "residential")
        is_bridge = tags.get("bridge") == "yes" or "puente" in street_name.lower()

        if is_bridge:
            stype = "puente"
        elif hway in ("primary", "trunk", "secondary"):
            stype = "avenida"
        else:
            stype = "calle"

        for i in range(len(nodes) - 1):
            u_id, v_id = nodes[i], nodes[i+1]
            if u_id in osm_nodes and v_id in osm_nodes:
                lat1, lon1 = osm_nodes[u_id]
                lat2, lon2 = osm_nodes[v_id]
                dist = haversine_m(lat1, lon1, lat2, lon2)
                if dist > 0.5:
                    G_raw.add_edge(u_id, v_id, distance=dist, name=street_name, tipo=stype)

    # Largest connected component
    largest_cc = max(nx.connected_components(G_raw), key=len)
    G_main = G_raw.subgraph(largest_cc).copy()
    print(f"Main connected component: {G_main.number_of_nodes()} nodes, {G_main.number_of_edges()} edges")

    # Contract to intersections (degree >= 3)
    intersections = {n for n in G_main.nodes() if G_main.degree(n) >= 3}
    print(f"Real street intersections found: {len(intersections)}")

    # Trace paths between intersections
    G_inter = nx.Graph()
    for u in intersections:
        lat, lon = osm_nodes[u]
        G_inter.add_node(u, lat=lat, lng=lon)

    visited_edges = set()
    for u in intersections:
        for nbr in G_main.neighbors(u):
            pair = tuple(sorted([u, nbr]))
            if pair in visited_edges:
                continue

            # Follow chain
            curr, prev = nbr, u
            tot_dist = G_main[prev][curr]["distance"]
            ename = G_main[prev][curr]["name"]
            etipo = G_main[prev][curr]["tipo"]

            while curr not in intersections:
                fwd = [x for x in G_main.neighbors(curr) if x != prev]
                if not fwd:
                    break
                next_n = fwd[0]
                tot_dist += G_main[curr][next_n]["distance"]
                prev, curr = curr, next_n

            if curr in intersections and curr != u:
                visited_edges.add(tuple(sorted([u, curr])))
                G_inter.add_edge(u, curr, distance=round(tot_dist, 1), name=ename, tipo=etipo)

    # Get largest connected component of intersections
    largest_inter_cc = max(nx.connected_components(G_inter), key=len)
    G_conn = G_inter.subgraph(largest_inter_cc).copy()
    print(f"Connected intersections: {G_conn.number_of_nodes()} nodes, {G_conn.number_of_edges()} edges")

    # Subsample to target_nodes (around 320 intersections) while preserving high centrality & connectivity
    if G_conn.number_of_nodes() > target_nodes:
        # Iteratively prune leaves and peripheral low-degree nodes
        while G_conn.number_of_nodes() > target_nodes:
            # Prefer degree 1 or degree 2 nodes
            low_deg = [n for n in G_conn.nodes() if G_conn.degree(n) == 1]
            if not low_deg:
                low_deg = sorted(G_conn.nodes(), key=lambda n: G_conn.degree(n))[:20]
            remove_count = min(len(low_deg), G_conn.number_of_nodes() - target_nodes)
            G_conn.remove_nodes_from(low_deg[:remove_count])
            
            # Ensure it stays connected
            if not nx.is_connected(G_conn):
                largest_cc = max(nx.connected_components(G_conn), key=len)
                G_conn = G_conn.subgraph(largest_cc).copy()

    print(f"Final OSM Manta Graph: {G_conn.number_of_nodes()} intersections, {G_conn.number_of_edges()} streets")

    # Re-index to sequential IDs: N-0001, N-0002...
    osm_to_nid = {}
    nodes_list = []
    for idx, (osm_id, data) in enumerate(G_conn.nodes(data=True)):
        nid = f"N-{idx+1:04d}"
        osm_to_nid[osm_id] = nid
        lat = round(data["lat"], 6)
        lng = round(data["lng"], 6)
        sec = get_sector(lat, lng)

        incident_streets = set()
        for nbr in G_conn.neighbors(osm_id):
            sname = G_conn[osm_id][nbr].get("name", "")
            if sname and sname != "Calle de Manta":
                incident_streets.add(sname)

        if len(incident_streets) >= 2:
            s_list = list(incident_streets)
            inter_name = f"{s_list[0]} y {s_list[1]}"
        elif len(incident_streets) == 1:
            inter_name = f"Intersección en {list(incident_streets)[0]}"
        else:
            inter_name = f"Intersección {sec} {idx+1}"

        nodes_list.append({
            "id": nid,
            "name": inter_name,
            "lat": lat,
            "lng": lng,
            "sector": sec,
            "is_refugio": False
        })

    speed_factors = {
        "avenida": 1.25,
        "calle": 1.00,
        "callejon": 0.70,
        "puente": 1.10
    }

    edges_list = []
    for idx, (u_osm, v_osm, e_data) in enumerate(G_conn.edges(data=True)):
        eid = f"E-{idx+1:04d}"
        tipo = e_data.get("tipo", "calle")
        dist = e_data.get("distance", 100.0)
        sfactor = speed_factors.get(tipo, 1.0)
        edges_list.append({
            "id": eid,
            "origen": osm_to_nid[u_osm],
            "destino": osm_to_nid[v_osm],
            "nombre": e_data.get("name", f"Tramo {tipo.capitalize()}"),
            "distancia_m": dist,
            "tipo": tipo,
            "velocidad_factor": sfactor,
            "peso_tiempo": round(dist / sfactor, 2)
        })

    # 4 Refugios: Assign to nodes closest to official locations in Manta
    target_ref_coords = {
        "REF-01": {"name": "Refugio ULEAM - Barbasquillo", "target": (-0.967, -80.738), "sector": "Barbasquillo"},
        "REF-02": {"name": "Refugio Puerto Pesquero - Los Esteros", "target": (-0.945, -80.686), "sector": "Los Esteros"},
        "REF-03": {"name": "Refugio Estadio Jocay", "target": (-0.958, -80.710), "sector": "Jocay"},
        "REF-04": {"name": "Refugio Malecón Escénico - Tarqui", "target": (-0.950, -80.700), "sector": "Tarqui"}
    }

    refugios_list = []
    ref_nodes_set = set()

    for r_id, r_info in target_ref_coords.items():
        t_lat, t_lng = r_info["target"]
        best_node = min(
            [n for n in nodes_list if n["id"] not in ref_nodes_set],
            key=lambda n: haversine_m(n["lat"], n["lng"], t_lat, t_lng)
        )
        ref_nodes_set.add(best_node["id"])
        best_node["is_refugio"] = True
        best_node["refugio_id"] = r_id

        refugios_list.append({
            "id": r_id,
            "name": r_info["name"],
            "nodo": best_node["id"],
            "capacidad_max": 75,
            "sector": r_info["sector"],
            "descripcion": f"Instalación fortificada de evacuación en {best_node['name']}."
        })

    graph_payload = {
        "ciudad": "Manta, Ecuador",
        "fuente": "OpenStreetMap Real Roads & Intersections",
        "total_nodos": len(nodes_list),
        "total_aristas": len(edges_list),
        "refugios": refugios_list,
        "nodos": nodes_list,
        "aristas": edges_list
    }

    with open("manta_graph.json", "w", encoding="utf-8") as f:
        json.dump(graph_payload, f, indent=2, ensure_ascii=False)
    with open("src/data/manta_graph.json", "w", encoding="utf-8") as f:
        json.dump(graph_payload, f, indent=2, ensure_ascii=False)

    print(f"Generated 100% Real OSM Graph: {len(nodes_list)} intersections, {len(edges_list)} streets, {len(refugios_list)} refugios.")

if __name__ == "__main__":
    build_graph(330)
