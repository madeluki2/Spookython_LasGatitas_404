"""
Configuration settings for Spookython 2026: Track A - Escape de Manta Zombie
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Security & API Key
# Challenge requires 'x-api-key' header authentication
API_KEY_HEADER_NAME = "x-api-key"
API_KEY = os.getenv("SPOOKY_API_KEY", "spooky-manta-key-2026")

# Server Configuration
SERVER_HOST = os.getenv("HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("PORT", "8000"))

# Game / Simulation Constants
DEFAULT_TURN_SECONDS = 2.0  # Challenge specifies 2-second turns
FAST_TURN_SECONDS = 0.5    # Accelerated mode for testing and fast demonstrations

# Path to Manta City Graph
GRAPH_FILE_PATH = os.path.join(BASE_DIR, "src", "data", "manta_graph.json")

# Street Speed Factors (higher factor = faster transit / lower cost)
SPEED_FACTORS = {
    "avenida": 1.25,
    "calle": 1.00,
    "callejon": 0.70,
    "puente": 1.10
}

# Fire Test Round Presets
FIRE_TEST_ROUNDS = {
    1: {
        "nombre": "Ronda 1 - Anochecer",
        "descripcion": "20 sobrevivientes, solo caminantes",
        "duracion_min": 5,
        "sobrevivientes_iniciales": 20,
        "zombies": {
            "caminante": 15,
            "corredor": 0,
            "horda": 0,
            "dormido": 0
        },
        "eventos": []
    },
    2: {
        "nombre": "Ronda 2 - Medianoche",
        "descripcion": "80 sobrevivientes, caminantes, corredores y hordas; colapso de puente",
        "duracion_min": 5,
        "sobrevivientes_iniciales": 80,
        "zombies": {
            "caminante": 30,
            "corredor": 15,
            "horda": 4,
            "dormido": 0
        },
        "eventos": [
            {
                "turno": 15,
                "tipo": "colapso_puente",
                "descripcion": "¡ALERTA MÁXIMA! El Puente Principal Río Tarqui ha colapsado por sismo e infestación.",
                "arista_nombre": "Puente Principal Río Tarqui"
            }
        ]
    },
    3: {
        "nombre": "Ronda 3 - Apocalipsis",
        "descripcion": "200 sobrevivientes a la vez, todos los tipos incluidos dormidos; 2 calles bloqueadas en vivo",
        "duracion_min": 5,
        "sobrevivientes_iniciales": 200,
        "zombies": {
            "caminante": 50,
            "corredor": 25,
            "horda": 6,
            "dormido": 30
        },
        "eventos": [
            {
                "turno": 10,
                "tipo": "bloqueo_calle",
                "descripcion": "¡CALLE BLOQUEADA! Barricada en llamas y escombros en Av. 4 de Noviembre.",
                "arista_nombre": "Av. 4 de Noviembre"
            },
            {
                "turno": 25,
                "tipo": "bloqueo_calle",
                "descripcion": "¡AVENIDA COLAPSADA! Horda masiva bloquea paso en Av. de la Cultura.",
                "arista_nombre": "Av. de la Cultura"
            }
        ]
    }
}
