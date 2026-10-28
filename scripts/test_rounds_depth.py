import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.engine.router import MantaRouter
from src.simulator.apocalypse_sim import ApocalypseSimulator

def run_deep_test():
    router = MantaRouter("src/data/manta_graph.json")
    sim = ApocalypseSimulator(router)

    for r in [1, 2, 3]:
        sim.reset_round(ronda=r)
        for _ in range(25):
            sim.execute_turn()
        st = sim.get_state()["stats"]
        print(f"Ronda {r} (25 turnos):")
        print(f"  Total: {st['total']} | Rescatados: {st['rescatados']} | Vivos: {st['vivos']} | Bajas: {st['mordidos']}")
        print(f"  Tasa Supervivencia: {st['supervivencia_pct']}% | Eficiencia: {st['eficiencia_pct']}%")
        print(f"  Latencia P95: {st['latencia_p95_ms']} ms | Max: {st['latencia_max_ms']} ms")
        print("-" * 50)

if __name__ == "__main__":
    run_deep_test()
