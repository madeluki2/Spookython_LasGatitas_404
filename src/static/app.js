/**
 * Escape de Manta Zombie - Frontend Application
 * Real-time emergency evacuation command center & interactive map
 */

// Global State
let map = null;
let graphData = null;
let worldState = null;
let ws = null;
let isAudioEnabled = true;
let audioCtx = null;
let selectedEntityId = null;

// Leaflet Layers
let streetsLayerGroup = null;
let blockedStreetsLayerGroup = null;
let refugiosLayerGroup = null;
let zombiesLayerGroup = null;
let survivorsLayerGroup = null;
let vansLayerGroup = null;
let routePolylineLayer = null;

// Street polylines and lookup indices
const streetLines = {}; // edge_id -> { poly, u, v, edge, geom }
const edgeByPair = {};  // "u:v" -> edge

// Initialize on page load
document.addEventListener("DOMContentLoaded", async () => {
  initMap();
  initAudio();
  await loadGraph();
  connectWebSocket();
});

// ==========================================================
// 1. MAP INITIALIZATION & TILES
// ==========================================================
function initMap() {
  // Center of Manta (between Tarqui, Jocay, and Malecón)
  const mantaCenter = [-0.954, -80.715];
  map = L.map("mantaMap", {
    center: mantaCenter,
    zoom: 14,
    minZoom: 12,
    maxZoom: 18,
    zoomControl: true,
    preferCanvas: true
  });

  // OpenStreetMap Open Tiles (100% libres y sin API Key requerida)
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    subdomains: ["a", "b", "c"],
    maxZoom: 19
  }).addTo(map);

  // Initialize Layer Groups
  streetsLayerGroup = L.layerGroup().addTo(map);
  blockedStreetsLayerGroup = L.layerGroup().addTo(map);
  refugiosLayerGroup = L.layerGroup().addTo(map);
  survivorsLayerGroup = L.layerGroup().addTo(map);
  vansLayerGroup = L.layerGroup().addTo(map);
  zombiesLayerGroup = L.layerGroup().addTo(map);
  routePolylineLayer = L.layerGroup().addTo(map);
}

// ==========================================================
// 2. GRAPH DATA & RENDERING
// ==========================================================
async function loadGraph() {
  try {
    const res = await fetch("/grafo");
    graphData = await res.json();
    renderGraphStreets(graphData);
    renderRefugios(graphData.refugios);
  } catch (err) {
    console.error("Error loading graph:", err);
  }
}

function renderGraphStreets(data) {
  streetsLayerGroup.clearLayers();
  const nodeMap = {};
  data.nodos.forEach(n => { nodeMap[n.id] = n; });

  data.aristas.forEach(edge => {
    edgeByPair[`${edge.origen}:${edge.destino}`] = edge;
    edgeByPair[`${edge.destino}:${edge.origen}`] = edge;

    const u = nodeMap[edge.origen];
    const v = nodeMap[edge.destino];
    if (!u || !v) return;

    // Glowing Tactical Blue Street Network Hierarchy
    let color = "#0284c7"; // Vibrant blue for all standard city streets (cuadras)
    let weight = 2.2;
    let opacity = 0.80;

    if (edge.tipo === "avenida") {
      color = "#38bdf8"; // Electric cyan-blue for major arterial avenues
      weight = 3.8;
      opacity = 0.95;
    } else if (edge.tipo === "puente") {
      color = "#f59e0b"; // Amber warning for bridges & viaducts
      weight = 5.0;
      opacity = 0.95;
    } else if (edge.tipo === "callejon") {
      color = "#0369a1"; // Deep azure blue for secondary alleys
      weight = 1.6;
      opacity = 0.65;
    }

    const geom = (edge.geometria && edge.geometria.length >= 2)
      ? edge.geometria
      : [[u.lat, u.lng], [v.lat, v.lng]];

    const poly = L.polyline(geom, {
      color: color,
      weight: weight,
      opacity: opacity,
      lineCap: "round",
      lineJoin: "round"
    });

    poly.bindTooltip(`<b>${edge.nombre}</b><br>Tipo: ${edge.tipo.toUpperCase()} · ${edge.distancia_m} m`, {
      sticky: true,
      className: "street-tooltip"
    });

    streetsLayerGroup.addLayer(poly);
    streetLines[edge.id] = { poly, u, v, edge, geom };
  });
}

function renderRefugios(refugios) {
  refugiosLayerGroup.clearLayers();
  const nodeMap = {};
  graphData.nodos.forEach(n => { nodeMap[n.id] = n; });

  refugios.forEach(ref => {
    const node = nodeMap[ref.nodo];
    if (!node) return;

    const iconHtml = `
      <div class="refugio-marker">
        <div class="ref-beacon-ring"></div>
        <div class="ref-icon-badge">🛡️</div>
      </div>
    `;

    const icon = L.divIcon({
      className: "custom-div-icon",
      html: iconHtml,
      iconSize: [36, 36],
      iconAnchor: [18, 18]
    });

    const marker = L.marker([node.lat, node.lng], { icon: icon });
    marker.bindPopup(`
      <div style="font-family: 'Outfit', sans-serif;">
        <h4 style="color: #10b981; margin-bottom: 4px;">🛡️ ${ref.name}</h4>
        <p style="font-size: 0.75rem; color: #cbd5e1; margin-bottom: 6px;">${ref.descripcion || ''}</p>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;">
          <b>Sector:</b> ${ref.sector}<br>
          <b>Nodo:</b> ${ref.nodo}<br>
          <b>Capacidad Máx:</b> ${ref.capacidad_max || 75} sobrevivientes
        </div>
      </div>
    `);
    refugiosLayerGroup.addLayer(marker);
  });
}

// ==========================================================
// 3. REAL-TIME WEBSOCKET & STATE STREAMING
// ==========================================================
function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log("WebSocket connected to Escape Manta engine");
    appendRadioLog("[ENLACE]", "Conexión satelital en vivo establecida con el Simulador.", "sistema");
  };

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.tipo === "bienvenida" || msg.tipo === "estado_actualizado" || msg.tipo === "ronda_cambiada") {
      updateWorldView(msg.data);
    }
  };

  ws.onclose = () => {
    console.warn("WebSocket closed. Retrying in 2 seconds...");
    setTimeout(connectWebSocket, 2000);
  };

  ws.onerror = (err) => {
    console.error("WebSocket error:", err);
  };
}

// Polling fallback if WebSocket drops
setInterval(async () => {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    try {
      const res = await fetch("/estado");
      const state = await res.json();
      updateWorldView(state);
    } catch (e) {}
  }
}, 1500);

// ==========================================================
// 4. WORLD VIEW UPDATE
// ==========================================================
function updateWorldView(state) {
  worldState = state;
  const nodeMap = {};
  if (graphData && graphData.nodos) {
    graphData.nodos.forEach(n => { nodeMap[n.id] = n; });
  }

  // 1. Update KPIs
  const stats = state.stats;
  document.getElementById("kpiSupervivencia").innerText = `${stats.supervivencia_pct}%`;
  document.getElementById("kpiSupervivenciaBar").style.width = `${stats.supervivencia_pct}%`;
  document.getElementById("kpiVivos").innerText = stats.vivos;
  document.getElementById("kpiTotal").innerText = stats.total;
  document.getElementById("kpiRescatados").innerText = stats.rescatados;
  document.getElementById("kpiMordidos").innerText = stats.mordidos;
  document.getElementById("kpiLatenciaP95").innerText = stats.latencia_p95_ms.toFixed(1);
  document.getElementById("kpiTurno").innerText = state.turno;

  // Update Play/Pause button appearance
  const playBtn = document.getElementById("btnPlayPausa");
  const playIcon = document.getElementById("playIcon");
  const playText = document.getElementById("playText");
  if (state.activo) {
    playBtn.classList.remove("play-btn");
    playBtn.classList.add("play-btn", "paused");
    playIcon.innerText = "⏸";
    playText.innerText = "PAUSAR";
  } else {
    playBtn.classList.remove("paused");
    playIcon.innerText = "▶";
    playText.innerText = "INICIAR";
  }

  // Update Round Buttons
  for (let r = 1; r <= 3; r++) {
    const btn = document.getElementById(`btnRonda${r}`);
    if (btn) {
      if (state.ronda === r) btn.classList.add("active");
      else btn.classList.remove("active");
    }
  }

  // 2. Update Blocked Streets on Map
  updateBlockedStreets(state.aristas_bloqueadas, nodeMap);

  // 3. Update Entities on Map
  updateSurvivorsOnMap(state.sobrevivientes, nodeMap);
  updateZombiesOnMap(state.zombies, nodeMap);
  updateVansOnMap(state.camionetas, nodeMap);

  // 4. Update Refuges Sidebar
  updateRefugiosSidebar(state.refugios);

  // 5. Update Radio Logs
  if (state.eventos && state.eventos.length > 0) {
    const latestEvent = state.eventos[state.eventos.length - 1];
    checkAndDisplayAlert(latestEvent);
  }

  // 6. Update Inspector if an entity is selected
  if (selectedEntityId) {
    refreshInspector();
  }
}

// ==========================================================
// 5. ENTITY RENDERING ON LEAFLET
// ==========================================================
function updateBlockedStreets(blockedEdgeIds, nodeMap) {
  blockedStreetsLayerGroup.clearLayers();
  const blockedSet = new Set(blockedEdgeIds);

  blockedEdgeIds.forEach(eid => {
    const item = streetLines[eid];
    if (!item) return;

    const geom = (item.geom && item.geom.length >= 2)
      ? item.geom
      : (item.edge && item.edge.geometria && item.edge.geometria.length >= 2)
      ? item.edge.geometria
      : [[item.u.lat, item.u.lng], [item.v.lat, item.v.lng]];

    const poly = L.polyline(geom, {
      color: "#ef4444",
      weight: 6,
      opacity: 0.95,
      dashArray: "8, 8",
      className: "blocked-pulse-street"
    });
    poly.bindTooltip(`🚨 <b>BLOQUEADA / COLAPSO</b><br>${item.edge.nombre}`, { sticky: true });
    blockedStreetsLayerGroup.addLayer(poly);
  });
}

function updateSurvivorsOnMap(survivors, nodeMap) {
  survivorsLayerGroup.clearLayers();

  survivors.forEach(s => {
    if (s.estado === "rescatado" || s.estado === "mordido") return;
    const node = nodeMap[s.nodo];
    if (!node) return;

    const isSelected = selectedEntityId === s.id;
    const iconHtml = `
      <div class="survivor-marker ${isSelected ? 'selected' : ''}" onclick="selectSurvivor('${s.id}')">
        <div class="surv-dot"></div>
      </div>
    `;

    const icon = L.divIcon({
      className: "custom-div-icon",
      html: iconHtml,
      iconSize: [16, 16],
      iconAnchor: [8, 8]
    });

    const marker = L.marker([node.lat, node.lng], { icon: icon });
    marker.on("click", () => selectSurvivor(s.id));
    survivorsLayerGroup.addLayer(marker);
  });
}

function updateZombiesOnMap(zombies, nodeMap) {
  zombiesLayerGroup.clearLayers();

  zombies.forEach(z => {
    const node = nodeMap[z.nodo];
    if (!node) return;

    let iconChar = "🧟";
    let extraClass = "";

    if (z.tipo === "corredor") {
      iconChar = "⚡";
      extraClass = "z-corredor";
    } else if (z.tipo === "horda") {
      iconChar = "☣️";
      extraClass = "z-horda";
      
      // Draw Horde Neighbor Hazard Area!
      const circle = L.circle([node.lat, node.lng], {
        color: "#ef4444",
        fillColor: "#ef4444",
        fillOpacity: 0.25,
        radius: 220,
        weight: 2,
        dashArray: "4, 4"
      });
      circle.bindTooltip(`⚠️ <b>ÁREA LETAL DE HORDA (${z.id})</b><br>Bloquea su nodo y todos los nodos vecinos`, { sticky: true });
      zombiesLayerGroup.addLayer(circle);

    } else if (z.tipo === "dormido") {
      iconChar = z.despierto ? "🧟" : "💤";
      extraClass = z.despierto ? "z-caminante" : "z-dormido";
    } else {
      extraClass = "z-caminante";
    }

    const iconHtml = `
      <div class="zombie-marker ${extraClass}">
        <span>${iconChar}</span>
      </div>
    `;

    const icon = L.divIcon({
      className: "custom-div-icon",
      html: iconHtml,
      iconSize: [22, 22],
      iconAnchor: [11, 11]
    });

    const marker = L.marker([node.lat, node.lng], { icon: icon });
    marker.bindTooltip(`<b>Zombie ${z.tipo.toUpperCase()} (${z.id})</b><br>Nodo: ${z.nodo}${z.tipo==='dormido' && !z.despierto ? ' (Inactivo)' : ''}`);
    zombiesLayerGroup.addLayer(marker);
  });
}

function updateVansOnMap(vans, nodeMap) {
  vansLayerGroup.clearLayers();
  if (!vans) return;

  vans.forEach(v => {
    const node = nodeMap[v.nodo];
    if (!node) return;

    const iconHtml = `
      <div class="van-marker">
        <span class="van-icon">🚐</span>
        <span class="van-badge">${v.ocupacion}/${v.capacidad_max}</span>
      </div>
    `;

    const icon = L.divIcon({
      className: "custom-div-icon",
      html: iconHtml,
      iconSize: [28, 28],
      iconAnchor: [14, 14]
    });

    const marker = L.marker([node.lat, node.lng], { icon: icon });
    marker.bindTooltip(`<b>Camioneta Rescate (${v.id})</b><br>Estado: ${v.estado}<br>Pasajeros: ${v.ocupacion}/${v.capacidad_max}`);
    vansLayerGroup.addLayer(marker);
  });
}

// ==========================================================
// 6. SURVIVOR INSPECTION & ESCAPE PATH VISUALIZATION
// ==========================================================
function selectSurvivor(survId) {
  selectedEntityId = survId;
  refreshInspector();
  playBeep(600, 0.08);
}

function refreshInspector() {
  if (!worldState || !selectedEntityId) return;
  const s = worldState.sobrevivientes.find(x => x.id === selectedEntityId);
  const container = document.getElementById("inspectorContent");
  if (!s) {
    container.innerHTML = `<div class="empty-inspector"><p>Sobreviviente no encontrado.</p></div>`;
    routePolylineLayer.clearLayers();
    return;
  }

  const nodeMap = {};
  graphData.nodos.forEach(n => { nodeMap[n.id] = n; });
  const currNode = nodeMap[s.nodo];

  // Draw Google Maps style GPS navigation polyline trail following exact asphalt road geometry
  routePolylineLayer.clearLayers();
  if (s.ruta_planificada && s.ruta_planificada.length > 1) {
    const routeCoords = [];
    for (let i = 0; i < s.ruta_planificada.length - 1; i++) {
      const uId = s.ruta_planificada[i];
      const vId = s.ruta_planificada[i + 1];
      const edge = edgeByPair[`${uId}:${vId}`];
      const uNode = nodeMap[uId];
      const vNode = nodeMap[vId];
      if (!uNode || !vNode) continue;

      if (edge && edge.geometria && edge.geometria.length >= 2) {
        let segmentGeom = edge.geometria.slice();
        // Check orientation of geometry
        const dStartToU = Math.hypot(segmentGeom[0][0] - uNode.lat, segmentGeom[0][1] - uNode.lng);
        const dEndToU = Math.hypot(segmentGeom[segmentGeom.length - 1][0] - uNode.lat, segmentGeom[segmentGeom.length - 1][1] - uNode.lng);
        if (dEndToU < dStartToU) {
          segmentGeom.reverse();
        }

        if (routeCoords.length > 0) {
          routeCoords.push(...segmentGeom.slice(1));
        } else {
          routeCoords.push(...segmentGeom);
        }
      } else {
        if (routeCoords.length === 0) routeCoords.push([uNode.lat, uNode.lng]);
        routeCoords.push([vNode.lat, vNode.lng]);
      }
    }

    if (routeCoords.length > 1) {
      // Outer glow casing (Google Maps route border)
      const polyBorder = L.polyline(routeCoords, {
        color: "#0369a1",
        weight: 8,
        opacity: 0.75,
        lineCap: "round",
        lineJoin: "round"
      });
      // Inner vibrant GPS route line
      const polyLine = L.polyline(routeCoords, {
        color: "#00f2fe",
        weight: 5,
        opacity: 1.0,
        lineCap: "round",
        lineJoin: "round"
      });
      routePolylineLayer.addLayer(polyBorder);
      routePolylineLayer.addLayer(polyLine);
    }
  }

  container.innerHTML = `
    <div class="inspect-card">
      <div class="inspect-title">🏃 SOBREVIVIENTE ${s.id}</div>
      <div class="inspect-row">
        <span class="inspect-k">Estado:</span>
        <span class="inspect-v c-${s.estado==='vivo'?'cyan':s.estado==='rescatado'?'green':'red'}">${s.estado.toUpperCase()}</span>
      </div>
      <div class="inspect-row">
        <span class="inspect-k">Nodo Actual:</span>
        <span class="inspect-v">${s.nodo}</span>
      </div>
      <div class="inspect-row">
        <span class="inspect-k">Ubicación:</span>
        <span class="inspect-v" style="font-size: 0.65rem;">${currNode ? currNode.name : 'Manta'}</span>
      </div>
      <div class="inspect-row">
        <span class="inspect-k">Pasos restantes a Refugio:</span>
        <span class="inspect-v">${s.ruta_planificada ? s.ruta_planificada.length - 1 : 0} calles</span>
      </div>
      <div class="inspect-row">
        <span class="inspect-k">Turnos en marcha:</span>
        <span class="inspect-v">${s.turnos_viajados}</span>
      </div>
    </div>
  `;
}

// ==========================================================
// 7. REFUGIOS SIDEBAR (NIVEL PRO BALANCING)
// ==========================================================
function updateRefugiosSidebar(refugios) {
  const container = document.getElementById("refugiosListContainer");
  if (!container || !refugios) return;

  container.innerHTML = refugios.map(r => {
    const pct = Math.min(100, Math.round((r.ocupacion / (r.capacidad_max || 75)) * 100));
    return `
      <div class="refugio-card">
        <div class="ref-top">
          <span class="ref-name">${r.name}</span>
          <span class="ref-count c-${pct > 80 ? 'gold' : 'green'}">${r.ocupacion} / ${r.capacidad_max || 75}</span>
        </div>
        <div class="ref-bar">
          <div class="ref-bar-fill" style="width: ${pct}%; background: ${pct > 80 ? '#fbbf24' : '#10b981'};"></div>
        </div>
      </div>
    `;
  }).join("");
}

// ==========================================================
// 8. RADIO BROADCAST, ALERTS & AUDIO SFX
// ==========================================================
let lastAlertId = null;

function checkAndDisplayAlert(eventObj) {
  if (!eventObj) return;
  const alertBanner = document.getElementById("liveAlertBanner");
  const alertText = document.getElementById("alertMessageText");

  if (eventObj.tipo === "evento_ciudad") {
    alertBanner.style.display = "flex";
    alertText.innerText = eventObj.descripcion;
    playSiren();
    setTimeout(() => { alertBanner.style.display = "none"; }, 8000);
  }

  // Append to radio log if new
  const logKey = `${eventObj.turno}-${eventObj.descripcion}`;
  if (lastAlertId !== logKey) {
    lastAlertId = logKey;
    appendRadioLog(`[${eventObj.tiempo}]`, eventObj.descripcion, eventObj.tipo);
    if (eventObj.tipo === "rescate") playBeep(880, 0.1);
  }
}

function appendRadioLog(timeStr, text, type) {
  const container = document.getElementById("radioLogContainer");
  if (!container) return;

  const entry = document.createElement("div");
  entry.className = `radio-log-entry ${type}`;
  entry.innerHTML = `
    <span class="log-time">${timeStr}</span>
    <span class="log-text">${text}</span>
  `;
  container.appendChild(entry);
  container.scrollTop = container.scrollHeight;
}

// Web Audio API Synthesizer
function initAudio() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    audioCtx = new AudioContext();
  } catch (e) {
    console.warn("Web Audio API not supported");
  }
}

function playBeep(freq = 440, duration = 0.1) {
  if (!isAudioEnabled || !audioCtx) return;
  try {
    if (audioCtx.state === "suspended") audioCtx.resume();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
    gain.gain.setValueAtTime(0.05, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + duration);
  } catch (e) {}
}

function playSiren() {
  if (!isAudioEnabled || !audioCtx) return;
  try {
    if (audioCtx.state === "suspended") audioCtx.resume();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(600, audioCtx.currentTime);
    osc.frequency.linearRampToValueAtTime(900, audioCtx.currentTime + 0.3);
    osc.frequency.linearRampToValueAtTime(600, audioCtx.currentTime + 0.6);
    gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.7);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.7);
  } catch (e) {}
}

function toggleAudio() {
  isAudioEnabled = !isAudioEnabled;
  document.getElementById("audioIcon").innerText = isAudioEnabled ? "🔊" : "🔇";
}

// ==========================================================
// 9. CONTROLS DISPATCH
// ==========================================================
async function togglePlayPausa() {
  playBeep(520, 0.08);
  if (!worldState) return;
  const endpoint = worldState.activo ? "/simulador/pausa" : "/simulador/play";
  await fetch(endpoint, { method: "POST" });
}

async function ejecutarPaso() {
  playBeep(700, 0.06);
  await fetch("/simulador/step", { method: "POST" });
}

async function reiniciarSimulacion() {
  playBeep(400, 0.12);
  await fetch("/simulador/reiniciar", { method: "POST" });
}

async function seleccionarRonda(rondaId) {
  playBeep(650, 0.1);
  await fetch(`/simulador/ronda/${rondaId}`, { method: "POST" });
}

async function cambiarVelocidad(segundos) {
  await fetch("/simulador/velocidad", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ segundos: parseFloat(segundos) })
  });
}
