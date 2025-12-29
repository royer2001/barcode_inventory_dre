"""
Script para generar el PDF del listado de responsables.
DRE Huánuco - Inventario 2025

Incluye funciones de limpieza y normalización de datos.

Uso: python generar_listado_responsables.py
"""

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.colors import black, gray
from db.database import create_connection
from datetime import datetime
import os
import re


# ============================================================
# DICCIONARIO DE CORRECCIONES MANUALES
# Formato: 'NOMBRE_INCORRECTO': 'NOMBRE_CORRECTO'
# Agregar aquí casos que necesiten corrección manual
# ============================================================
CORRECCIONES_MANUALES = {
    # Casos detectados en formato APELLIDOS NOMBRES -> NOMBRES APELLIDOS
    'ALVAREZ LAZARO LIVIO SANTIAGO': 'LIVIO SANTIAGO ALVAREZ LAZARO',
    'AMADEO REYMUNDEZ SANCHEZ': 'AMADEO REYMUNDEZ SANCHEZ',  # Verificar si es correcto
    'ANAYA ALVARADO DELFINA': 'DELFINA ANAYA ALVARADO',
    'ATENCIA ARBI JIM CLAVER': 'JIM CLAVER ATENCIA ARBI',
    'CABRERA SUAREZ EVELYN': 'EVELYN CABRERA SUAREZ',
    'CAJA LEON COTRINA FLAVIO': 'FLAVIO CAJA LEON COTRINA',
    'CAJALEON COTRINA FLAVIO': 'FLAVIO CAJALEON COTRINA',
    'CHAHUA SILVA YAKELIN ARMANDINA': 'YAKELIN ARMANDINA CHAHUA SILVA',
    'CIERTO AGUI NEYDER': 'NEYDER CIERTO AGUI',
    'COPELLO QUINTANA WILLIAM GUSTAVO': 'WILLIAM GUSTAVO COPELLO QUINTANA',
    'CORONEL ALVAREZ RONALD': 'RONALD CORONEL ALVAREZ',
    'CRUZ VENANCIO MIGUEL ANGEL': 'MIGUEL ANGEL CRUZ VENANCIO',
    'CUEVA GALIANO MARCIA REGINA': 'MARCIA REGINA CUEVA GALIANO',
    'ESPINOZA GARAY JOSE LUIS': 'JOSE LUIS ESPINOZA GARAY',
    'TREJO LUGO TANIA ROSSY': 'TANIA ROSSY TREJO LUGO',
    'VARA LUCAS FIORELLA': 'FIORELLA VARA LUCAS',
    'VERA TOLENTINO LIZ CINTHIA': 'LIZ CINTHIA VERA TOLENTINO',
    'VERA TOLENTNO LIZ CINTHIA': 'LIZ CINTHIA VERA TOLENTINO',  # Typo en TOLENTNO
    'VIVAS Y BARRUETA GLADIS MELBA': 'GLADIS MELBA VIVAS Y BARRUETA',
    'GLADYS FRANCISCA LAURENCIO DEL VALLE -COORDINADORA TÉCNICA': 'GLADYS FRANCISCA LAURENCIO DEL VALLE',
    'GONZALES SANTIAGO JOCSAN ELIAS': 'JOCSAN ELIAS GONZALES SANTIAGO',
    'GONZLAES SANTIAGO JOCSAN ELIAS': 'JOCSAN ELIAS GONZALES SANTIAGO',  # Typo en GONZLAES
    # Agregar más casos según se detecten...
}


def limpiar_responsable(nombre):
    """
    Limpia y normaliza el nombre del responsable.
    
    Reglas de limpieza:
    1. Elimina espacios extras
    2. Convierte a mayúsculas para uniformidad
    3. Elimina prefijos profesionales (ABOG., CPC., DR., ING., LIC., etc.)
    4. Normaliza el formato de comas
    5. Elimina valores inválidos (nan, None, etc.)
    """
    if not nombre or nombre.lower() in ['nan', 'none', '', ' ']:
        return None
    
    # Convertir a string y eliminar espacios extras
    nombre = str(nombre).strip()
    nombre = ' '.join(nombre.split())  # Elimina espacios múltiples
    
    # Convertir a mayúsculas
    nombre = nombre.upper()
    
    # Lista de prefijos profesionales a eliminar
    # El patrón maneja casos con o sin espacio después del punto
    prefijos = [
        r'^ABOG\.?\s*',
        r'^ADM\.?\s*',
        r'^CPC\.?\s*',
        r'^DR\.?\s*',
        r'^DRA\.?\s*',
        r'^ECO\.?\s*',
        r'^ECON\.?\s*',
        r'^ING\.?\s*',
        r'^LIC\.?\s*',
        r'^MG\.?\s*',
        r'^MGR\.?\s*',
        r'^PROF\.?\s*',
        r'^PSIC\.?\s*',
        r'^SR\.?\s*',
        r'^SRA\.?\s*',
        r'^SRTA\.?\s*',
        r'^TEC\.?\s*',
    ]
    
    # Aplicar limpieza de prefijos múltiples veces (para casos como LIC. ADM. NOMBRE)
    nombre_anterior = None
    while nombre != nombre_anterior:
        nombre_anterior = nombre
        for prefijo in prefijos:
            nombre = re.sub(prefijo, '', nombre, flags=re.IGNORECASE)
        nombre = nombre.strip()
    
    # Quitar comas (el formato ya es NOMBRES, APELLIDOS, solo quitamos la coma)
    nombre = nombre.replace(',', '')
    
    # Eliminar espacios múltiples que puedan quedar
    nombre = ' '.join(nombre.split())
    
    # Aplicar correcciones manuales si existen
    if nombre in CORRECCIONES_MANUALES:
        nombre = CORRECCIONES_MANUALES[nombre]
    
    return nombre if nombre else None


def obtener_responsables_limpios():
    """
    Obtiene la lista de responsables desde la BD y los limpia.
    Retorna un diccionario con responsables únicos y cantidad de bienes asignados.
    """
    conn = create_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT responsable, oficina, COUNT(*) as cantidad
        FROM bienes 
        WHERE responsable IS NOT NULL 
          AND responsable != '' 
          AND responsable != 'nan'
        GROUP BY responsable, oficina
        ORDER BY responsable, oficina
    """)
    
    resultados = cursor.fetchall()
    conn.close()
    
    # Diccionario para agrupar por responsable limpio
    responsables = {}
    
    for resp_original, oficina, cantidad in resultados:
        resp_limpio = limpiar_responsable(resp_original)
        
        if resp_limpio:
            if resp_limpio not in responsables:
                responsables[resp_limpio] = {
                    'oficinas': {},
                    'total': 0,
                    'originales': set()
                }
            
            # Agregar oficina y cantidad
            if oficina not in responsables[resp_limpio]['oficinas']:
                responsables[resp_limpio]['oficinas'][oficina] = 0
            responsables[resp_limpio]['oficinas'][oficina] += cantidad
            responsables[resp_limpio]['total'] += cantidad
            responsables[resp_limpio]['originales'].add(resp_original)
    
    return responsables


def generar_listado_pdf(output_dir="assets/generated_barcodes"):
    """Genera un PDF con el listado de responsables."""
    
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"LISTADO_RESPONSABLES_{timestamp}.pdf")
    
    pdf = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    # Obtener datos limpios
    responsables = obtener_responsables_limpios()
    
    def draw_header(y):
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawCentredString(width/2, y, "LISTADO DE RESPONSABLES")
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
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(1.5*cm, y, "N°")
        pdf.drawString(2.2*cm, y, "RESPONSABLE")
        pdf.drawString(12*cm, y, "OFICINA(S)")
        pdf.drawString(17.5*cm, y, "BIENES")
        y -= 5
        pdf.setLineWidth(0.5)
        pdf.line(1.5*cm, y, width - 1.5*cm, y)
        return y - 10

    def draw_row(y, num, nombre, oficinas, total):
        # Número
        pdf.setFont("Helvetica", 8)
        pdf.drawString(1.5*cm, y, str(num))
        
        # Nombre (truncar si es muy largo)
        pdf.setFont("Helvetica", 8)
        nombre_display = nombre[:45] + "..." if len(nombre) > 45 else nombre
        pdf.drawString(2.2*cm, y, nombre_display)
        
        # Oficinas (solo la primera si hay muchas)
        oficina_list = list(oficinas.keys())
        if len(oficina_list) > 1:
            oficina_display = f"{oficina_list[0][:20]}... (+{len(oficina_list)-1})"
        else:
            oficina_display = oficina_list[0][:25] if oficina_list else "-"
        pdf.drawString(12*cm, y, oficina_display)
        
        # Total de bienes
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawRightString(18.5*cm, y, str(total))
        
        return y - 12

    # Generar PDF
    y = height - 2.5*cm
    y = draw_header(y)
    y = draw_table_header(y)
    
    # Ordenar por nombre
    responsables_ordenados = sorted(responsables.items(), key=lambda x: x[0])
    total_bienes = 0
    
    for num, (nombre, datos) in enumerate(responsables_ordenados, 1):
        if y < 2*cm:
            pdf.showPage()
            y = height - 2*cm
            y = draw_table_header(y)
        
        y = draw_row(y, num, nombre, datos['oficinas'], datos['total'])
        total_bienes += datos['total']
    
    # Resumen final de la primera sección
    y -= 10
    pdf.setLineWidth(0.5)
    pdf.line(1.5*cm, y, width - 1.5*cm, y)
    y -= 15
    
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(2*cm, y, f"TOTAL: {len(responsables_ordenados)} responsables")
    pdf.drawRightString(18.5*cm, y, f"{total_bienes} bienes")
    
    # ============================================================
    # SEGUNDA SECCIÓN: RESPONSABLES POR ÁREA/OFICINA
    # ============================================================
    
    def draw_header_oficinas(y):
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawCentredString(width/2, y, "RESPONSABLES POR ÁREA / OFICINA")
        y -= 20
        
        pdf.setFont("Helvetica", 10)
        pdf.setFillColor(gray)
        fecha = datetime.now().strftime("%d/%m/%Y")
        pdf.drawCentredString(width/2, y, f"DRE Huánuco - Inventario 2025")
        pdf.setFillColor(black)
        y -= 12
        
        pdf.setLineWidth(0.5)
        pdf.line(2*cm, y, width - 2*cm, y)
        return y - 15
    
    def draw_oficina_title(y, oficina, cantidad):
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(1.5*cm, y, f"▸ {oficina}")
        pdf.setFont("Helvetica", 9)
        pdf.drawRightString(18.5*cm, y, f"({cantidad} bienes)")
        return y - 12
    
    def draw_responsable_row(y, nombre, cantidad):
        pdf.setFont("Helvetica", 9)
        nombre_display = nombre[:55] + "..." if len(nombre) > 55 else nombre
        pdf.drawString(2.5*cm, y, f"• {nombre_display}")
        pdf.drawRightString(18.5*cm, y, str(cantidad))
        return y - 11
    
    # Reorganizar datos por oficina
    por_oficina = {}
    for nombre, datos in responsables.items():
        for oficina, cantidad in datos['oficinas'].items():
            if oficina not in por_oficina:
                por_oficina[oficina] = {'responsables': {}, 'total': 0}
            if nombre not in por_oficina[oficina]['responsables']:
                por_oficina[oficina]['responsables'][nombre] = 0
            por_oficina[oficina]['responsables'][nombre] += cantidad
            por_oficina[oficina]['total'] += cantidad
    
    # Nueva página para la segunda sección
    pdf.showPage()
    y = height - 2.5*cm
    y = draw_header_oficinas(y)
    
    # Ordenar oficinas alfabéticamente
    for oficina in sorted(por_oficina.keys()):
        datos_oficina = por_oficina[oficina]
        
        # Verificar espacio para título + al menos 2 responsables
        if y < 4*cm:
            pdf.showPage()
            y = height - 2*cm
        
        y = draw_oficina_title(y, oficina, datos_oficina['total'])
        
        # Ordenar responsables de esta oficina
        for nombre in sorted(datos_oficina['responsables'].keys()):
            if y < 2*cm:
                pdf.showPage()
                y = height - 2*cm
            
            cantidad = datos_oficina['responsables'][nombre]
            y = draw_responsable_row(y, nombre, cantidad)
        
        y -= 5  # Espacio entre oficinas
    
    # Resumen final
    y -= 10
    pdf.setLineWidth(0.5)
    pdf.line(1.5*cm, y, width - 1.5*cm, y)
    y -= 15
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawCentredString(width/2, y, f"Total: {len(por_oficina)} áreas/oficinas")
    
    pdf.save()
    return output_path, len(responsables_ordenados), total_bienes


def mostrar_duplicados_potenciales():
    """
    Identifica posibles duplicados para revisión manual.
    """
    responsables = obtener_responsables_limpios()
    
    # Buscar nombres similares
    nombres = list(responsables.keys())
    duplicados = []
    
    for i, nombre1 in enumerate(nombres):
        for nombre2 in nombres[i+1:]:
            # Comparar apellidos (primera palabra antes de coma o espacio)
            apellido1 = nombre1.split(',')[0].split()[0] if nombre1 else ""
            apellido2 = nombre2.split(',')[0].split()[0] if nombre2 else ""
            
            if apellido1 and apellido2 and apellido1 == apellido2:
                # Verificar si comparten más palabras
                palabras1 = set(nombre1.replace(',', ' ').split())
                palabras2 = set(nombre2.replace(',', ' ').split())
                comunes = palabras1 & palabras2
                
                if len(comunes) >= 2:
                    duplicados.append((nombre1, nombre2, comunes))
    
    return duplicados


if __name__ == "__main__":
    print("=" * 60)
    print("  GENERADOR DE LISTADO DE RESPONSABLES")
    print("  DRE Huánuco - Inventario 2025")
    print("=" * 60)
    print()
    
    # Generar PDF
    output, total_resp, total_bienes = generar_listado_pdf()
    
    print(f"✅ PDF generado exitosamente:")
    print(f"   {output}")
    print()
    print(f"📊 Resumen:")
    print(f"   • Responsables únicos: {total_resp}")
    print(f"   • Total de bienes asignados: {total_bienes}")
    print()
    
    # Mostrar posibles duplicados
    print("🔍 Verificando posibles duplicados...")
    duplicados = mostrar_duplicados_potenciales()
    
    if duplicados:
        print(f"\n⚠️  Se encontraron {len(duplicados)} posibles duplicados:")
        for nombre1, nombre2, comunes in duplicados[:10]:  # Mostrar solo 10
            print(f"   • '{nombre1}' vs '{nombre2}'")
        if len(duplicados) > 10:
            print(f"   ... y {len(duplicados) - 10} más")
    else:
        print("   ✓ No se encontraron duplicados evidentes")
    
    print()
    print("=" * 60)
