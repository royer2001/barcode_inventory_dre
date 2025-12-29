"""
Script para generar el PDF del diccionario de claves de áreas/oficinas.
DRE Huánuco - Inventario 2025

Uso: python generar_diccionario_claves.py
"""

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.colors import black, gray
from utils.barcode_generator import OFFICE_KEYS
from datetime import datetime
import os


def generar_diccionario_pdf(output_dir="assets/generated_barcodes"):
    """Genera un PDF con el diccionario de claves de oficinas."""
    
    # Asegurar que el directorio existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Nombre del archivo con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"DICCIONARIO_CLAVES_{timestamp}.pdf")
    
    pdf = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    def draw_header(y):
        """Dibuja el encabezado del documento."""
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawCentredString(width/2, y, "DICCIONARIO DE CLAVES DE ÁREAS")
        y -= 22
        
        pdf.setFont("Helvetica", 12)
        pdf.drawCentredString(width/2, y, "DRE Huánuco - Inventario 2025")
        y -= 18
        
        pdf.setFont("Helvetica", 9)
        pdf.setFillColor(gray)
        fecha = datetime.now().strftime("%d/%m/%Y")
        pdf.drawCentredString(width/2, y, f"Fecha: {fecha}")
        pdf.setFillColor(black)
        y -= 12
        
        pdf.setLineWidth(0.5)
        pdf.line(2*cm, y, width - 2*cm, y)
        return y - 15

    def draw_table_header(y):
        """Dibuja el encabezado de la tabla."""
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(2.5*cm, y, "CLAVE")
        pdf.drawString(5*cm, y, "ÁREA / OFICINA")
        y -= 5
        pdf.setLineWidth(0.5)
        pdf.line(2*cm, y, width - 2*cm, y)
        return y - 12

    def draw_category(y, title):
        """Dibuja el título de una categoría."""
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(2*cm, y, title)
        return y - 15

    def draw_row(y, clave, oficina):
        """Dibuja una fila de la tabla."""
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(2.5*cm, y, f"[{clave}]")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(5*cm, y, oficina)
        return y - 14

    # Organizar claves por categorías
    categories = {
        "DGA - Dirección General de Administración": 
            sorted([(v, k) for k, v in OFFICE_KEYS.items() if k.startswith('DGA')]),
        "DGI - Dirección General Institucional": 
            sorted([(v, k) for k, v in OFFICE_KEYS.items() if k.startswith('DGI')]),
        "DGP - Dirección General Pedagógica": 
            sorted([(v, k) for k, v in OFFICE_KEYS.items() if k.startswith('DGP')]),
        "Otras Áreas": 
            sorted([(v, k) for k, v in OFFICE_KEYS.items() 
                    if not any([k.startswith('DGA'), k.startswith('DGI'), k.startswith('DGP')])])
    }

    # Generar contenido
    y = height - 2.5*cm
    y = draw_header(y)
    y = draw_table_header(y)

    for category, items in categories.items():
        # Nueva página si no hay espacio
        if y < 3*cm:
            pdf.showPage()
            y = height - 2*cm
            y = draw_table_header(y)
        
        y = draw_category(y, category)
        
        for clave, oficina in items:
            if y < 2*cm:
                pdf.showPage()
                y = height - 2*cm
                y = draw_table_header(y)
            
            y = draw_row(y, clave, oficina)
        
        y -= 8

    # Pie de página
    y -= 5
    pdf.setLineWidth(0.5)
    pdf.line(2*cm, y, width - 2*cm, y)
    y -= 15
    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(width/2, y, f"Total: {len(OFFICE_KEYS)} claves registradas")

    pdf.save()
    return output_path


if __name__ == "__main__":
    print("=" * 50)
    print("  GENERADOR DE DICCIONARIO DE CLAVES")
    print("  DRE Huánuco - Inventario 2025")
    print("=" * 50)
    print()
    
    print(f"📋 Claves registradas: {len(OFFICE_KEYS)}")
    print()
    
    output = generar_diccionario_pdf()
    
    print(f"✅ PDF generado exitosamente:")
    print(f"   {output}")
    print()
    print("=" * 50)
