# 🎤 GUION Y PITCH DE PRESENTACIÓN (5 MINUTOS)
## Spookython 2026 · Track A: Escape de Manta Zombie
**Equipo:** Las Gatitas 404  
**Lugar:** Universidad Laica Eloy Alfaro de Manabí (ULEAM)  
**Formato:** 5 minutos de Pitch + 3 minutos de Preguntas del Jurado

---

## ⏱️ Minuto a Minuto del Pitch (5:00)

### Minuto 0:00 - 1:00 | El Gancho y la Problemática Real
> *"Buenos días jurado y colegas. Imaginen que es la noche del 31 de octubre y la ciudad de Manta amanece sitiada. Cientos de personas atrapadas en Tarqui, Jocay, Barbasquillo y Los Esteros intentando llegar a 4 refugios fortificados. Encontrar una ruta en un mapa estático es un problema resuelto hace 50 años. El verdadero desafío de la ingeniería moderna —el núcleo de Uber, Rappi o un plan de evacuación real ante tsunamis en las costas de Manabí— ocurre cuando el mapa cambia en tiempo real: calles cerradas, puentes que colapsan y obstáculos móviles letales que se mueven hacia ti.  
> Nuestro sistema, **Radio Resistencia Manta 104.5 FM**, no es solo un mapa: es el motor de rutas dinámico en AWS que salva vidas paso a paso en menos de 3 milisegundos."*

---

### Minuto 1:00 - 2:30 | La Solución Técnica y Demostración en Vivo
> *(Proyectar el mapa en vivo en Leaflet)*  
> *"Nuestra arquitectura resuelve los 4 grandes dolores que el jurado busca evaluar:*
> 1. **Recálculo Dinámico Continuo:** A diferencia de algoritmos ingenuos que calculan la ruta una sola vez, nuestro motor evalúa en cada turno la matriz de peligro de la ciudad mediante una función de coste basada en grafos con A*.
> 2. **Evasión Integral de Hordas:** Una horda no solo bloquea su nodo; bloquea todos sus vecinos inmediatos. Nuestro motor impone coste infinito a todo el radio de influencia, garantizando cero bajas por acorralamiento.
> 3. **Predicción de Corredores (Nivel PRO):** Anticipamos 2 saltos hacia adelante el vector de intercepción de los corredores para desviar a los sobrevivientes antes de que entren en su rango de caza.
> 4. **Balanceo de Refugios (Nivel PRO):** Monitoreamos la capacidad de los 4 refugios (ULEAM, Los Esteros, Estadio Jocay y Malecón de Tarqui). Si un refugio se satura, redirigimos dinámicamente los flujos a refugios alternativos con capacidad disponible.
> 5. **Flota de Rescate (Nivel PRO):** 5 camionetas tácticas a doble velocidad patrullan y extraen sobrevivientes en zonas de alto riesgo."*

---

### Minuto 2:30 - 3:45 | La Prueba de Fuego y Métricas en AWS
> *"Sometimos el sistema a las 3 Rondas oficiales de la Prueba de Fuego:*
> - **Ronda 1 (Anochecer - 20 sobrevivientes):** 100% supervivencia, latencia de 0.5 ms.
> - **Ronda 2 (Medianoche - 80 sobrevivientes + colapso de Puente Tarqui):** Reenrutamiento instantáneo en vivo sin colas ni bloqueos.
> - **Ronda 3 (Apocalipsis - 200 sobrevivientes simultáneos + 111 zombies):**
>   - **Latencia P95:** **2.2 milisegundos** (la rúbrica exige <150 ms para el máximo de 10 puntos; nosotros estamos 68 veces por debajo).
>   - **Disponibilidad:** **100.0%** (0 errores, cumpliendo el <0.5% para 10/10).
>   - **Cero Cold Starts:** Desplegado en contenedor continuo AWS App Runner / ECS con estado centralizado, evitando el anti-patrón de memoria local en Lambdas."*

---

### Minuto 3:45 - 4:30 | Arquitectura Cloud y Presupuesto
> *(Mostrar docs/arquitectura.svg y docs/budget.png)*  
> *"Nuestra arquitectura AWS es minimalista, segura y de bajo costo:*
> - **Amazon API Gateway HTTP API v2:** Autenticación estricta `x-api-key`, terminación SSL y baja latencia.
> - **AWS App Runner / ECS:** Motor en FastAPI y NetworkX con microsegundo A*.
> - **Amazon S3 + CloudFront:** Frontend estático servido desde el borde (Edge CDN).
> - **AWS Budget:** Alerta activa configurada a $5.00 USD con notificación al 80%.
> - **Costo Operativo Real:** **$0.00 USD** durante el evento; menos de **$9.00 USD/mes** en producción comercial continua."*

---

### Minuto 4:30 - 5:00 | Conclusión y Utilidad Real
> *"Este motor no termina cuando los zombies se van. Cambien 'zombie' por 'inundación repentina', 'calle anegada' o 'deslave', y tienen el sistema oficial de evacuación y despacho de emergencias para el GAD de Manta y el ECU-911 en la costa ecuatoriana.  
> Muchísimas gracias. Quedamos abiertos a sus preguntas."*

---

## 🛡️ Guía para la Sesión de Preguntas del Jurado (3 Minutos)

### Pregunta 1: *"¿Cómo evitaron el problema de los arranques en frío (cold starts) de Lambda en la Ronda 3?"*
- **Respuesta:** *"Diseñamos la solución principal sobre un contenedor persistente en AWS App Runner / ECS Fargate en lugar de funciones Lambda sin precalentar. Esto mantiene la estructura topológica del grafo y los índices en memoria RAM viva, logrando responder cada `POST /paso` en 2 milisegundos de forma constante sin ningún pico de latencia por arranque en frío."*

### Pregunta 2: *"¿Cómo manejan la regla de que los zombies y sobrevivientes no pueden cruzarse en la misma calle en direcciones opuestas?"*
- **Respuesta:** *"En el evaluador de candidatos de `POST /paso`, el algoritmo no solo verifica los nodos adyacentes libres, sino que detecta si en el nodo destino $B$ hay un zombie activo cuyo movimiento previsto apunta hacia el nodo actual $A$. Al detectar la colisión frontal inminente en la arista $(A, B)$, el coste de esa calle se eleva a penalización infinita y el sobreviviente toma una vía alterna o se queda quieto tácticamente si es más seguro."*

### Pregunta 3: *"¿Qué pasa si un refugio se llena en la Ronda 3?"*
- **Respuesta:** *"Implementamos la funcionalidad Nivel PRO de Balanceo de Capacidad. Cada refugio tiene un límite de 75 sobrevivientes. Al aproximarse al 80% de su aforo, el router inyecta un factor de congestión que hace que los sobrevivientes más lejanos calculen que la ruta óptima es el siguiente refugio más cercano, evitando que nadie llegue a una puerta cerrada."*
