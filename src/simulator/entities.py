"""
Data models and entities for the Apocalypse Simulation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Any

@dataclass
class ZombieEntity:
    id: str
    tipo: str  # 'caminante', 'corredor', 'horda', 'dormido'
    nodo: str
    nodo_anterior: Optional[str] = None
    despierto: bool = True
    contador_turnos: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tipo": self.tipo,
            "nodo": self.nodo,
            "nodo_anterior": self.nodo_anterior,
            "despierto": self.despierto
        }

@dataclass
class SobrevivienteEntity:
    id: str
    nodo: str
    nodo_anterior: Optional[str] = None
    estado: str = "vivo"  # 'vivo', 'rescatado', 'mordido', 'en_camioneta'
    ruta_planificada: List[str] = field(default_factory=list)
    turnos_viajados: int = 0
    distancia_optima_inicial: float = 0.0
    refugio_alcanzado: Optional[str] = None
    camioneta_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "nodo": self.nodo,
            "nodo_anterior": self.nodo_anterior,
            "estado": self.estado,
            "ruta_planificada": self.ruta_planificada,
            "turnos_viajados": self.turnos_viajados,
            "refugio_alcanzado": self.refugio_alcanzado,
            "camioneta_id": self.camioneta_id
        }

@dataclass
class CamionetaRescateEntity:
    """Nivel PRO: Flota de 5 camionetas tácticas para rescate rápido"""
    id: str
    nodo: str
    capacidad_max: int = 4
    pasajeros: List[str] = field(default_factory=list)
    estado: str = "patrullando"  # 'patrullando', 'rescatando', 'rumbo_refugio'
    refugio_base: str = "REF-01"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "nodo": self.nodo,
            "capacidad_max": self.capacidad_max,
            "pasajeros": self.pasajeros,
            "estado": self.estado,
            "ocupacion": len(self.pasajeros)
        }
