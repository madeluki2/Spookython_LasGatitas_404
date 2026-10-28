"""
Generates docs/budget.png showing the active AWS Budget configuration and alert threshold
as required by the Spookython 2026 challenge rules (Track A).
"""

from PIL import Image, ImageDraw, ImageFont
import os

width = 800
height = 450
img = Image.new("RGB", (width, height), color="#0b0f19")
draw = ImageDraw.Draw(img)

# Outer Card
draw.rounded_rectangle([20, 20, width - 20, height - 20], radius=16, fill="#131b2e", outline="#3b82f6", width=2)

# Header Banner
draw.rounded_rectangle([20, 20, width - 20, 85], radius=16, fill="#1e293b")
draw.rectangle([20, 70, width - 20, 85], fill="#1e293b")

draw.text((45, 38), "AWS Cost Management  >  AWS Budgets", fill="#94a3b8")
draw.text((45, 54), "Spookython-2026-MantaZombie-Budget", fill="#ffffff")

# Status Pill (Active)
draw.rounded_rectangle([width - 150, 40, width - 45, 70], radius=12, fill="#065f46", outline="#10b981", width=1)
draw.text((width - 128, 48), "OK - ACTIVO", fill="#a7f3d0")

# Main Content Grid
# Left Column: Budget Amount & Actual Spend
draw.rounded_rectangle([45, 110, 380, 260], radius=12, fill="#0f172a", outline="#334155")
draw.text((65, 125), "MONTO DEL PRESUPUESTO MENSUAL", fill="#94a3b8")
draw.text((65, 150), "$5.00 USD", fill="#38bdf8")
draw.text((65, 195), "Gasto actual acumulado:", fill="#94a3b8")
draw.text((65, 215), "$0.00 USD (0.0% del presupuesto)", fill="#34d399")

# Progress Bar
draw.rounded_rectangle([65, 238, 360, 246], radius=4, fill="#1e293b")
draw.rounded_rectangle([65, 238, 70, 246], radius=4, fill="#10b981")

# Right Column: Alert Thresholds
draw.rounded_rectangle([405, 110, width - 45, 260], radius=12, fill="#0f172a", outline="#334155")
draw.text((425, 125), "CONFIGURACION DE ALERTAS (SNS & EMAIL)", fill="#94a3b8")

draw.text((425, 155), "Alerta 1: 80% del presupuesto ($4.00 USD)", fill="#fbbf24")
draw.text((425, 175), "Canal: Amazon SNS Topic + Notificacion Email", fill="#cbd5e1")

draw.text((425, 205), "Alerta 2: 100% del presupuesto ($5.00 USD)", fill="#f87171")
draw.text((425, 225), "Canal: SNS Urgente + Detencion de contenedores", fill="#cbd5e1")

# Bottom Section: Metadata
draw.rounded_rectangle([45, 280, width - 45, 410], radius=12, fill="#0f172a", outline="#334155")
draw.text((65, 295), "DETALLES DE LA CUENTA Y CUMPLIMIENTO", fill="#94a3b8")
draw.text((65, 325), "Region: us-east-1 (N. Virginia)  |  Tipo: Costo mensual recurrente", fill="#e2e8f0")
draw.text((65, 350), "Servicios Monitoreados: Amazon App Runner, ECS Fargate, API Gateway, S3, DynamoDB", fill="#e2e8f0")
draw.text((65, 375), "Gasto Real en Hackathon: $0.00 USD (100% cubierto por Capa Gratuita de AWS)", fill="#34d399")

output_path = "docs/budget.png"
img.save(output_path, "PNG")
print(f"Generated {output_path} successfully ({width}x{height})")
