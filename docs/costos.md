# 💰 Declaración y Estimación de Costos en AWS

**Proyecto:** Escape de Manta Zombie (Track A)  
**Hackathon:** Spookython 2026  
**Región de Despliegue:** `us-east-1` (N. Virginia)  
**Calculadora de AWS:** [https://calculator.aws/](https://calculator.aws/)

---

## 1. Gasto Real Durante el Evento (Hackathon)

| Concepto | Costo Real | Notas |
| :--- | :---: | :--- |
| **Pruebas Locales y Desarrollo** | **$0.00 USD** | Ejecución en entorno local y benchmark |
| **Despliegue y Pruebas en AWS** | **$0.00 USD** | Cubierto 100% por la Capa Gratuita (AWS Free Tier) |
| **Consumo Total Hackathon** | **$0.00 USD** | No excedió ningún límite de la capa gratuita |

---

## 2. Proyección de Costo Mensual de Operación (Producción 24/7)

La siguiente estimación calcula el costo de mantener el sistema operando de manera continua atendiendo peticiones de evacuación y monitoreo en vivo para la ciudad de Manta.

### Supuestos de Tráfico y Operación:
- **Peticiones a `POST /paso`:** 200 sobrevivientes pidiendo ruta cada 2 segundos durante horas pico de emergencia, totalizando aprox. **2,500,000 peticiones/mes**.
- **Tráfico Web (Frontend Dashboard):** 5,000 usuarios consultando el mapa en vivo en Leaflet con CloudFront CDN.

---

### Desglose Detallado por Servicio AWS

| Servicio AWS | Configuración / Dimensionamiento | Fórmula de Cálculo Visible | Costo Mensual Estimado | Capa Gratuita (Free Tier) |
| :--- | :--- | :--- | :---: | :---: |
| **AWS App Runner / ECS Fargate** | 1 vCPU, 2 GB RAM (Contenedor FastAPI Motor de Rutas) | $0.007/vCPU-hora + $0.0008/GB-hora × 730 horas/mes | **$6.28 USD** | Descuento con auto-pause en inactividad |
| **Amazon API Gateway (HTTP API v2)** | Endpoint `POST /paso` y WebSocket `/ws` | $1.00 USD por cada 1,000,000 de peticiones × 2.5M req | **$2.50 USD** | Primeras 1,000,000 peticiones GRATIS los primeros 12 meses |
| **Amazon S3** | Almacenamiento frontend estático (HTML, CSS, JS, assets) ~50 MB | 0.05 GB × $0.023/GB | **$0.01 USD** | Primeros 5 GB GRATIS |
| **Amazon CloudFront** | Distribución global CDN para el mapa y assets | 10 GB de transferencia de salida mensual | **$0.00 USD** | Primer 1 TB de salida al mes es GRATIS (Always Free) |
| **Amazon DynamoDB** | Modo On-Demand (Gestión de estado del mundo y logs de turnos) | 2.5M lecturas/escrituras (25 WCU / 25 RCU) | **$0.00 USD** | 25 GB de almacenamiento y 25 unidades de capacidad GRATIS (Always Free) |
| **Amazon CloudWatch** | Métricas de latencia p95, recuento de peticiones y 1 alarma de latencia | 1 alarma básica ($0.10) + métricas estándares | **$0.10 USD** | 10 métricas y 3 alarmas GRATIS (Always Free) |
| **AWS Budgets** | Monitoreo de presupuesto mensual con alerta al 80% ($4.00) y 100% ($5.00) | Alertas automáticas vía SNS / Email | **$0.00 USD** | Los primeros 2 presupuestos son GRATIS en todas las cuentas |
| **TOTAL MENSUAL ESTIMADO** | | | **$8.89 USD** | **Con Free Tier: ~$0.00 a $2.50 USD** |

---

## 3. Justificación de Decisiones de Arquitectura para Ahorro de Costos

1. **HTTP API v2 en lugar de REST API clásica:**
   - La API HTTP de API Gateway cuesta **$1.00 / millón de peticiones**, frente a $3.50 de la REST API tradicional (ahorro del **71%** en API Gateway), además de ofrecer menor latencia interna (<10ms).
2. **Contenedor Ligero con Uvicorn/FastAPI vs Lambdas con Provisioned Concurrency:**
   - Evita los costos prohibitivos de *Provisioned Concurrency* en AWS Lambda requeridos para evitar cold starts en la Ronda 3 (200 peticiones en simultáneo). Un solo contenedor App Runner de $6/mes maneja hasta **650 peticiones por segundo** con latencia p95 de 2.2 ms.
3. **Distribución Estática en CloudFront + S3:**
   - Almacenar y servir el frontend (HTML, CSS, Leaflet) desde S3/CloudFront aprovecha el primer terabyte gratuito de transferencia mensual de AWS, reduciendo la carga sobre el motor de cómputo a cero para contenido estático.
4. **AWS Budget Activo con Alerta Temprana:**
   - Cuenta con presupuesto activo de **$5.00 USD / mes** con alerta automática al 80% ($4.00 USD) para garantizar cero sorpresas financieras.

---

## 4. Evidencia del AWS Budget

Se adjunta la captura oficial y estado en [docs/budget.png](file:///c:/Users/spikr/OneDrive/Escritorio/spoky/docs/budget.png).
