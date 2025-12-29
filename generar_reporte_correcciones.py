"""
Script para generar un reporte PDF de correcciones realizadas.
DRE Huánuco - Inventario 2025

Documenta los problemas detectados y las acciones de corrección
en los datos de responsables y áreas/oficinas.

Uso: python generar_reporte_correcciones.py
"""

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.colors import black, gray
from datetime import datetime
import os

# Importar las correcciones definidas
from generar_listado_responsables import CORRECCIONES_MANUALES
from utils.barcode_generator import OFFICE_KEYS


def generar_reporte_pdf(output_dir="assets/generated_barcodes"):
    """Genera un PDF con el reporte de correcciones realizadas."""
    
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"REPORTE_CORRECCIONES_{timestamp}.pdf")
    
    pdf = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    def draw_title(y, text):
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(2*cm, y, text)
        y -= 5
        pdf.setLineWidth(0.5)
        pdf.line(2*cm, y, width - 2*cm, y)
        return y - 15

    def draw_subtitle(y, text):
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(2*cm, y, text)
        return y - 12

    def draw_text(y, text, indent=0):
        pdf.setFont("Helvetica", 9)
        pdf.drawString(2*cm + indent, y, text)
        return y - 11

    def draw_correction(y, original, corregido):
        pdf.setFont("Helvetica", 8)
        # Original (truncado si es muy largo)
        orig_display = original[:40] + "..." if len(original) > 40 else original
        pdf.drawString(2.5*cm, y, f"• {orig_display}")
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(11*cm, y, "→")
        pdf.setFont("Helvetica", 8)
        corr_display = corregido[:35] + "..." if len(corregido) > 35 else corregido
        pdf.drawString(11.5*cm, y, corr_display)
        return y - 10

    # ============================================================
    # PÁGINA 1: ENCABEZADO Y RESUMEN
    # ============================================================
    y = height - 2.5*cm
    
    # Título principal
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width/2, y, "REPORTE DE CORRECCIONES DE DATOS")
    y -= 22
    
    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(width/2, y, "DRE Huánuco - Inventario 2025")
    y -= 18
    
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(gray)
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    pdf.drawCentredString(width/2, y, f"Generado: {fecha}")
    pdf.setFillColor(black)
    y -= 25
    
    # Resumen
    y = draw_title(y, "1. RESUMEN EJECUTIVO")
    
    y = draw_text(y, f"• Total de correcciones manuales de nombres: {len(CORRECCIONES_MANUALES)}")
    y = draw_text(y, f"• Total de claves de oficinas definidas: {len(OFFICE_KEYS)}")
    y -= 10
    
    # ============================================================
    # SECCIÓN 2: PROBLEMAS DETECTADOS EN NOMBRES
    # ============================================================
    y = draw_title(y, "2. PROBLEMAS DETECTADOS EN NOMBRES DE RESPONSABLES")
    
    problemas_nombres = [
        ("Prefijos profesionales", "ABOG., CPC., DR., LIC., ING., ADM., PSIC., PROF., etc."),
        ("Prefijos múltiples", "LIC. ADM., DR. ING., etc. (dos o más prefijos juntos)"),
        ("Prefijos pegados", "ADM.NOMBRE, LIC.NOMBRE (sin espacio después del punto)"),
        ("Formato con coma", "NOMBRES, APELLIDOS (coma separando nombres de apellidos)"),
        ("Formato invertido", "APELLIDOS NOMBRES (sin coma, orden incorrecto)"),
        ("Cargos incluidos", "Nombre -CARGO, Nombre (CARGO), etc."),
        ("Errores tipográficos", "GONZLAES en lugar de GONZALES, TOLENTNO en lugar de TOLENTINO"),
        ("Tildes inconsistentes", "SANCHEZ vs SÁNCHEZ, CAJALEÓN vs CAJALEON"),
    ]
    
    for problema, descripcion in problemas_nombres:
        if y < 3*cm:
            pdf.showPage()
            y = height - 2*cm
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(2.5*cm, y, f"• {problema}:")
        pdf.setFont("Helvetica", 9)
        pdf.drawString(6.5*cm, y, descripcion)
        y -= 12
    
    y -= 10
    
    # ============================================================
    # SECCIÓN 3: ACCIONES DE LIMPIEZA AUTOMÁTICA
    # ============================================================
    if y < 5*cm:
        pdf.showPage()
        y = height - 2*cm
    
    y = draw_title(y, "3. ACCIONES DE LIMPIEZA AUTOMÁTICA")
    
    acciones_auto = [
        "Eliminación de prefijos profesionales (ABOG., CPC., DR., LIC., ADM., PSIC., etc.)",
        "Eliminación de prefijos múltiples en bucle hasta que no queden más",
        "Conversión a MAYÚSCULAS para uniformidad",
        "Eliminación de comas en los nombres",
        "Eliminación de espacios múltiples",
        "Eliminación de espacios al inicio y final",
    ]
    
    for accion in acciones_auto:
        if y < 2*cm:
            pdf.showPage()
            y = height - 2*cm
        y = draw_text(y, f"• {accion}", indent=0.5*cm)
    
    y -= 10
    
    # ============================================================
    # SECCIÓN 4: CORRECCIONES MANUALES
    # ============================================================
    if y < 5*cm:
        pdf.showPage()
        y = height - 2*cm
    
    y = draw_title(y, "4. CORRECCIONES MANUALES APLICADAS")
    
    y = draw_subtitle(y, f"Total: {len(CORRECCIONES_MANUALES)} correcciones")
    y -= 5
    
    for original, corregido in sorted(CORRECCIONES_MANUALES.items()):
        if y < 2*cm:
            pdf.showPage()
            y = height - 2*cm
        y = draw_correction(y, original, corregido)
    
    y -= 10
    
    # ============================================================
    # SECCIÓN 5: CLAVES DE OFICINAS
    # ============================================================
    pdf.showPage()
    y = height - 2*cm
    
    y = draw_title(y, "5. CLAVES DE ÁREAS/OFICINAS DEFINIDAS")
    
    y = draw_subtitle(y, f"Total: {len(OFFICE_KEYS)} claves de 4 letras")
    y -= 5
    
    # Agrupar por categoría
    categorias = {
        "DGA": [(k, v) for k, v in OFFICE_KEYS.items() if k.startswith('DGA')],
        "DGI": [(k, v) for k, v in OFFICE_KEYS.items() if k.startswith('DGI')],
        "DGP": [(k, v) for k, v in OFFICE_KEYS.items() if k.startswith('DGP')],
        "OTRAS": [(k, v) for k, v in OFFICE_KEYS.items() 
                  if not any([k.startswith('DGA'), k.startswith('DGI'), k.startswith('DGP')])],
    }
    
    for cat, items in categorias.items():
        if y < 4*cm:
            pdf.showPage()
            y = height - 2*cm
        
        y = draw_subtitle(y, f"{cat} ({len(items)} claves)")
        
        for oficina, clave in sorted(items):
            if y < 2*cm:
                pdf.showPage()
                y = height - 2*cm
            pdf.setFont("Helvetica-Bold", 8)
            pdf.drawString(2.5*cm, y, f"[{clave}]")
            pdf.setFont("Helvetica", 8)
            oficina_display = oficina[:50] + "..." if len(oficina) > 50 else oficina
            pdf.drawString(4.5*cm, y, oficina_display)
            y -= 10
        
        y -= 5
    
    # ============================================================
    # SECCIÓN 6: RECOMENDACIONES
    # ============================================================
    pdf.showPage()
    y = height - 2*cm
    
    y = draw_title(y, "6. RECOMENDACIONES PARA FUTUROS REGISTROS")
    
    recomendaciones = [
        "Usar formato consistente: NOMBRES APELLIDOS (sin comas)",
        "No incluir prefijos profesionales (ABOG., CPC., DR., etc.)",
        "No incluir cargos junto al nombre",
        "Verificar ortografía antes de registrar",
        "Usar tildes de forma consistente",
        "Verificar que el área/oficina coincida con las definidas en el sistema",
    ]
    
    for rec in recomendaciones:
        y = draw_text(y, f"• {rec}", indent=0.5*cm)
    
    # Pie de página
    y -= 30
    pdf.setLineWidth(0.5)
    pdf.line(2*cm, y, width - 2*cm, y)
    y -= 15
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.setFillColor(gray)
    pdf.drawCentredString(width/2, y, "Documento generado automáticamente - Sistema de Inventario DRE Huánuco")
    
    pdf.save()
    return output_path


if __name__ == "__main__":
    print("=" * 60)
    print("  GENERADOR DE REPORTE DE CORRECCIONES")
    print("  DRE Huánuco - Inventario 2025")
    print("=" * 60)
    print()
    
    output = generar_reporte_pdf()
    
    print(f"✅ PDF generado exitosamente:")
    print(f"   {output}")
    print()
    print(f"📊 Contenido del reporte:")
    print(f"   • Resumen ejecutivo")
    print(f"   • Problemas detectados en nombres")
    print(f"   • Acciones de limpieza automática")
    print(f"   • {len(CORRECCIONES_MANUALES)} correcciones manuales")
    print(f"   • {len(OFFICE_KEYS)} claves de oficinas")
    print(f"   • Recomendaciones")
    print()
    print("=" * 60)
