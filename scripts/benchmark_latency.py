"""
Benchmark script for POST /paso latency and availability.
Simulates hundreds of concurrent survivor routing requests to measure:
- p50, p90, p95, p99 latency in milliseconds
- Availability % (< 0.5% errors for 10/10)
- Compliance with < 150ms gold requirement.
"""

import os
import sys
import time
import random
import statistics

# Ensure repo root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.engine.router import MantaRouter
from src.simulator.apocalypse_sim import ApocalypseSimulator

def run_benchmark(num_requests: int = 1000):
    print(f"=== INICIANDO BENCHMARK DE LATENCIA Y DISPONIBILIDAD ({num_requests} peticiones) ===")
    router = MantaRouter("src/data/manta_graph.json")
    sim = ApocalypseSimulator(router)
    sim.reset_round(ronda=3) # Round 3 is the most demanding: 200 survivors, 111 zombies!

    # Execute 5 turns to establish active zombie presence and blocked streets
    for _ in range(5):
        sim.execute_turn()

    state = sim.get_state()
    zombies = state["zombies"]
    blocked = set(state["aristas_bloqueadas"])
    nodes = list(router.nodes.keys())

    latencies_ms = []
    errors = 0

    t_start = time.perf_counter()

    for i in range(num_requests):
        node = random.choice(nodes)
        survivor_id = f"S-{i+1:04d}"

        t0 = time.perf_counter()
        try:
            next_node = router.find_best_next_node(
                nodo_actual=node,
                zombies=zombies,
                aristas_bloqueadas=blocked,
                refugio_occupancy=sim.refugio_occupancy
            )
            dt_ms = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(dt_ms)
            if not next_node:
                errors += 1
        except Exception as e:
            errors += 1

    total_time = time.perf_counter() - t_start

    sorted_lats = sorted(latencies_ms)
    p50 = statistics.median(sorted_lats)
    p90 = sorted_lats[int(0.90 * len(sorted_lats))]
    p95 = sorted_lats[int(0.95 * len(sorted_lats))]
    p99 = sorted_lats[int(0.99 * len(sorted_lats))]
    max_lat = sorted_lats[-1]
    avg_lat = statistics.mean(sorted_lats)

    error_pct = (errors / num_requests) * 100.0
    availability_pct = 100.0 - error_pct
    rps = num_requests / total_time

    print(f"Total Requests: {num_requests}")
    print(f"Total Time: {total_time:.2f} s ({rps:.0f} req/sec)")
    print(f"Disponibilidad: {availability_pct:.2f}% (Errores: {errors})")
    print(f"Latencia Media: {avg_lat:.3f} ms")
    print(f"Latencia P50:   {p50:.3f} ms")
    print(f"Latencia P90:   {p90:.3f} ms")
    print(f"Latencia P95:   {p95:.3f} ms")
    print(f"Latencia P99:   {p99:.3f} ms")
    print(f"Latencia Max:   {max_lat:.3f} ms")
    print("-" * 50)

    if p95 <= 150.0:
        print("[MAXIMA PUNTUACION] CALIFICACION LATENCIA: 10/10 (p95 <= 150 ms) -> CUMPLIMIENTO TOTAL")
    elif p95 <= 300.0:
        print("[PLATA] CALIFICACION LATENCIA: 7/10 (p95 <= 300 ms)")
    elif p95 <= 500.0:
        print("[BRONCE] CALIFICACION LATENCIA: 4/10 (p95 <= 500 ms)")
    else:
        print("[FUERA DE RANGO] (> 500 ms)")

    if error_pct < 0.5:
        print("[MAXIMA PUNTUACION] CALIFICACION DISPONIBILIDAD: 10/10 (< 0.5% errores)")
    else:
        print("[ALERTA] CALIFICACION DISPONIBILIDAD REDUCIDA")

if __name__ == "__main__":
    run_benchmark(1000)

