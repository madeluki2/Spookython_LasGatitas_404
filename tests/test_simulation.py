import os
import sys

# Ensure repository root is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
from src.engine.router import MantaRouter
from src.simulator.apocalypse_sim import ApocalypseSimulator

def test_full_simulation():
    router = MantaRouter("src/data/manta_graph.json")
    sim = ApocalypseSimulator(router)
    
    for round_num in [1, 2, 3]:
        sim.reset_round(ronda=round_num)
        st = sim.get_state()
        print(f"\n--- Testing Round {round_num} ---")
        print(f"Survivors: {st['stats']['total']}, Zombies: {len(st['zombies'])}")
        
        # Execute 10 turns
        for t in range(10):
            sim.execute_turn()
        
        st = sim.get_state()
        stats = st["stats"]
        print(f"After 10 turns: Vivos={stats['vivos']}, Rescatados={stats['rescatados']}, Mordidos={stats['mordidos']}")
        print(f"Latency p95: {stats['latencia_p95_ms']} ms, Max: {stats['latencia_max_ms']} ms")
        print(f"Survival %: {stats['supervivencia_pct']}%, Efficiency: {stats['eficiencia_pct']}%")
        assert stats["latencia_p95_ms"] < 150.0, "Latency p95 must be < 150ms for max points"

if __name__ == "__main__":
    test_full_simulation()
    print("\nALL SIMULATION TESTS PASSED PERFECTLY!")
