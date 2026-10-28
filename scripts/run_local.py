"""
Local runner script to launch the FastAPI server and simulation engine.
"""

import os
import sys
from pathlib import Path

# Ensure repo root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import uvicorn
from src.config import SERVER_HOST, SERVER_PORT

if __name__ == "__main__":
    print(f"===========================================================")
    print(f"  ESCAPE DE MANTA ZOMBIE - SERVIDOR ACTIVO")
    print(f"  Web Dashboard: http://localhost:{SERVER_PORT}")
    print(f"  Swagger Docs:  http://localhost:{SERVER_PORT}/docs")
    print(f"===========================================================")
    uvicorn.run("src.api.server:app", host="127.0.0.1", port=SERVER_PORT, reload=False)
