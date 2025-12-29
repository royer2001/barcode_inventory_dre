from reportlab.lib.utils import ImageReader
from io import BytesIO
from PIL import Image, ImageDraw
from typing import Tuple
import os
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
import platform

OUTPUT_DIR = "assets/generated_barcodes"


# ----------------- CONFIGURACIÓN -----------------
OUTPUT_DIR = "assets/generated_barcodes"
DPI = 600
CM_TO_INCH = 1 / 2.54
WIDTH_CM, HEIGHT_CM = 5.94, 3
TARGET_WIDTH = int(WIDTH_CM * CM_TO_INCH * DPI)
TARGET_HEIGHT = int(HEIGHT_CM * CM_TO_INCH * DPI)
BORDER_RADIUS = 35
BORDER_WIDTH = 3
BORDER_COLOR = "black"
MARGIN = 6
MAX_WIDTH_RATIO = 0.9
MAX_HEIGHT_RATIO = 0.6
LOGO_RATIO_W = 0.15
LOGO_RATIO_H = 0.22

# ================================================================
# ESPECIFICACIONES DE CÓDIGOS DE BARRAS EAN-13/Code128
# ================================================================
# DIMENSIONES RECOMENDADAS:
#   Tamaño Nominal (100%):  37.29 mm (ancho) x 25.91 mm (alto)
#   Tamaño Mínimo (80%):    29.83 mm (ancho) x 20.73 mm (alto)
#   Tamaño Máximo (200%):   75.58 mm (ancho) x 82.00 mm (alto)
#   Mínimo Práctico:        30 mm x 20 mm (garantiza lectura)
#
# CONSIDERACIONES CLAVE:
#   1. ZONA TRANQUILA (Márgenes): Espacio blanco a los lados del
#      código para que el escáner lo detecte. Sin tinta ni texto.
#   2. ESCALADO: Proporcional entre 80% y 200%. No alterar solo
#      ancho o alto individualmente.
#   3. CONTRASTE: Fondo blanco + barras negras (ideal para lectura)
#   4. UBICACIÓN: Área plana y visible, sin curvas ni pliegues.
#   5. LOGOS/TEXTOS: Fuera de la zona de barras y sus márgenes.
# ================================================================
MIN_BARCODE_WIDTH_MM = 37.0   # Ancho nominal ~37.29mm
MIN_BARCODE_HEIGHT_MM = 26.0  # Alto nominal ~25.91mm
# Convertir a píxeles a 600 DPI
MIN_BARCODE_WIDTH_PX = int(MIN_BARCODE_WIDTH_MM / 10 * CM_TO_INCH * DPI)
MIN_BARCODE_HEIGHT_PX = int(MIN_BARCODE_HEIGHT_MM / 10 * CM_TO_INCH * DPI)
# ================================================================

# Diccionario de claves de 4 letras para cada área/oficina
OFFICE_KEYS = {
    # Áreas de la DGA (Dirección General de Administración)
    "ABAST-CHOFER": "ABCH",
    "ALMACEN PATRIMONIO": "ALPA",
    "ARCHIVO": "ARCH",
    "AUDITORIO": "AUDI",
    "CONSTANCIA DE PAGOS": "CPAG",
    "CONSTANCIAS DE PAGOS": "CPAG",
    "DESPACHO DIRECTORAL": "DESP",
    "DGA-ABASTECIMIENTO": "DGAB",
    "DGA-ALMACÉN": "DGAL",
    "DGA-CONTABILIDAD": "DGAC",
    "DGA-DIRECCIÓN": "DGAD",
    "DGA-PATRIMONIO": "DGAP",
    "DGA-SECRETARIA": "DGAS",
    "DGA-TESORERIA": "DGAT",
    
    # Áreas de la DGI (Dirección General de Institucional)
    "DGI-DIRECCIÓN": "DGID",
    "DGI-ESTADÍSTICA": "DGIE",
    "DGI-INFORMÁTICA": "DGII",
    "DGI-INFRAESTRUCTURA": "DGIF",
    "DGI-PLANIFICACIÓN": "DGIP",
    "DGI-PLANIFINACIÓN": "DGIP",  # Variante con typo
    "DGI-PRESUPUESTO": "DGPR",
    "DGI-RACIONALIZACION": "DGIR",
    "DGI-SECRETARIA": "DGIS",
    
    # Áreas de la DGP (Dirección General Pedagógica)
    "DGP-DIRECCIÓN": "DGPD",
    "DGP-ESPECIALISTA DE EDUCACIÓN FISICA": "DGEF",
    "DGP-ESPECIALISTA DE EDUCACIÓN OFI. 25": "DG25",
    "DGP-ESPECIALISTA DE EDUCACIÓN OFI. 26": "DG26",
    "DGP-PROGRAMA 107": "P107",
    "DGP-PROGRAMA 9002": "P902",
    
    # Otras áreas
    "DIRECCIÓN": "DIRE",
    "ESCALAFON": "ESCA",
    "I.S.P MARCOS DURAN MARTEL": "ISPM",
    "MESA PARTES": "MESP",
    "OAJ": "OAJJ",
    "OAJ-DIRECCION": "OAJD",
    "OAJ-SECRETARIA": "OAJS",
    "OCI-DIRECCIÓN": "OCID",
    "ORGANO DE CONTROL INSTITUCIONAL": "OCII",
    "PERSONAL DE VIGILANCIA": "VIGI",
    "PROGRAMA - PREVAED": "PREV",
    "PROGRAMA PPTCD - 0051": "P051",
    "RECURSOS HUMANOS": "RRHH",
    "RELACIONES PUBLICAS": "RRPP",
    "RR.HH - BIENESTAR SOCIAL": "RHBS",
    "RR.HH - PLANILLAS": "RHPL",
    "RR.HH - SECRETARIA TECNICA": "RHST",
    "SECRETARIA-GENERAL": "SECG",
    "SERVICIOS GENERALES": "SERG",
}


def get_office_key(office_name: str) -> str:
    """Obtiene la clave de 4 letras para una oficina dada."""
    if not office_name:
        return "XXXX"
    
    # Buscar coincidencia exacta primero
    office_upper = office_name.strip().upper()
    if office_upper in OFFICE_KEYS:
        return OFFICE_KEYS[office_upper]
    
    # Buscar coincidencia parcial (por si el nombre tiene variaciones)
    for key, code in OFFICE_KEYS.items():
        if key in office_upper or office_upper in key:
            return code
    
    # Si no se encuentra, generar una clave genérica basada en las primeras letras
    words = office_name.strip().split()
    if len(words) >= 2:
        # Tomar las primeras 2 letras de las primeras 2 palabras
        return (words[0][:2] + words[1][:2]).upper()[:4].ljust(4, 'X')
    else:
        # Tomar las primeras 4 letras
        return office_name.strip().upper()[:4].ljust(4, 'X')


def _create_canvas() -> Tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("L", (TARGET_WIDTH, TARGET_HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    # Sin borde para evitar interferencia con otros elementos
    return img, draw


def _generate_base_barcode(codigo: str) -> Image.Image:
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Sanitize codigo to avoid path issues - replace problematic characters
    sanitized = codigo.replace('/', '_').replace('\\', '_')
    tmp_path = os.path.join(OUTPUT_DIR, f"{sanitized}_temp")
    
    writer = ImageWriter()
    writer.dpi = 600
    # Especificaciones basadas en diagrama técnico:
    # - Ancho barras: ~80% del ancho total
    # - Altura barras: 31.8mm (escalado a nuestra etiqueta = ~18mm)
    # - Zona silenciosa: 4.8mm mínimo a cada lado
    writer.module_width = 0.4  # Ancho de cada barra en mm
    writer.module_height = 18.0  # Altura de las barras en mm (proporción del diagrama)
    writer.write_text = False
    # Zona silenciosa: ~5mm a cada lado (aprox 12 módulos de 0.4mm)
    writer.quiet_zone = 12
    
    # Guardar sin texto debajo
    Code128(codigo, writer=writer).save(tmp_path, options={"write_text": False})

    img = Image.open(tmp_path + ".png").convert("L")
    os.remove(tmp_path + ".png")
    return img


def _resize_barcode(img: Image.Image) -> Image.Image:
    """Redimensiona el código de barras siguiendo especificaciones técnicas."""
    # Según diagrama: código ocupa 80% del ancho total (122.428/152.428)
    max_w = int(TARGET_WIDTH * 0.80)
    # Altura máxima disponible para el barcode (sin texto debajo)
    max_h = int(TARGET_HEIGHT * 0.45)
    
    # Calcular escala proporcional (para no distorsionar las barras)
    scale = min(max_w / img.width, max_h / img.height)
    
    new_w = int(img.width * scale)
    new_h = int(img.height * scale)
    
    # Asegurar dimensiones mínimas recomendadas
    if new_w < MIN_BARCODE_WIDTH_PX:
        new_w = MIN_BARCODE_WIDTH_PX
    if new_h < MIN_BARCODE_HEIGHT_PX:
        new_h = MIN_BARCODE_HEIGHT_PX
    
    # Redimensionar si es necesario
    if new_w != img.width or new_h != img.height:
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    return img


def _draw_centered_text(draw, text, y, font) -> int:
    text_w = draw.textlength(text, font=font)
    draw.text(((TARGET_WIDTH - text_w) / 2, y), text, fill="black", font=font)
    return y + int(font.size * 1.2)


def _add_logo(canvas: Image.Image, logo_path: str):
    if not os.path.exists(logo_path):
        return

    # Convertir logo a NEGRO PURO (sin grises) para impresión óptima
    logo = Image.open(logo_path).convert("RGBA")
    
    # Crear fondo blanco para aplanar transparencias
    background = Image.new("L", logo.size, 255)  # 255 = blanco
    
    if "A" in logo.getbands():
        alpha = logo.split()[3]
        logo_gray = logo.convert("L")
        background.paste(logo_gray, mask=alpha)
        logo = background
    else:
        logo = logo.convert("L")
    
    # Aplicar umbral para convertir a NEGRO PURO (0) y BLANCO PURO (255)
    # Cualquier píxel más oscuro que 180 se vuelve negro, el resto blanco
    threshold = 180
    logo = logo.point(lambda p: 0 if p < threshold else 255)

    # Tamaño máximo deseado basado en porcentaje del sticker
    max_w = int(TARGET_WIDTH * LOGO_RATIO_W)
    max_h = int(TARGET_HEIGHT * LOGO_RATIO_H)

    # Obtener proporción original
    w, h = logo.size
    # Factor que mantiene proporción y no excede el máximo
    scale = min(max_w / w, max_h / h)

    # ✅ Nueva dimensión manteniendo aspecto
    new_w = int(w * scale)
    new_h = int(h * scale)

    logo = logo.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Posición (esquina inferior izquierda con pequeño margen)
    x = 10  # Margen izquierdo pequeño
    y = TARGET_HEIGHT - logo.height - 10  # Margen inferior pequeño

    canvas.paste(logo, (x, y))


def generate_barcode(codigo: str, title: str = "", logo_path: str = "utils/logo.png", detalle_bien: str = "", save_file: bool = False, tipo_registro: str = "", oficina: str = ""):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1️⃣ Lienzo base
    canvas_img, draw = _create_canvas()

    # 2️⃣ Generar barcode
    barcode_img = _resize_barcode(_generate_base_barcode(codigo))

    # 3️⃣ Fuentes más grandes para mejor legibilidad
    font_title = get_font(size=42, bold=True)  # Denominación del bien
    font_detalle = get_font(size=34)  # Título inventario
    font_area = get_font(size=38)  # Área / Oficina
    font_office_key = get_font(size=48, bold=True)  # Clave de oficina (GRANDE)

    # Margen izquierdo para alineación
    margin_left = 25
    
    # 🔑 CLAVE DE OFICINA (esquina superior derecha)
    office_key = get_office_key(oficina)
    key_width = draw.textlength(office_key, font=font_office_key)
    
    # Dibujar un rectángulo de fondo para destacar la clave
    key_padding = 8
    key_x = TARGET_WIDTH - key_width - margin_left - key_padding
    key_y = 8
    
    # Rectángulo con borde negro para la clave
    rect_x1 = key_x - key_padding
    rect_y1 = key_y - 4
    rect_x2 = key_x + key_width + key_padding
    rect_y2 = key_y + font_office_key.size + 4
    draw.rectangle([rect_x1, rect_y1, rect_x2, rect_y2], outline="black", width=3)
    
    # Texto de la clave
    draw.text((key_x, key_y), office_key, fill="black", font=font_office_key)
    
    # Ancho disponible para texto (dejando espacio para la clave)
    max_text_width = rect_x1 - margin_left - 15
    
    # 4️⃣ Dibujar textos alineados a la izquierda
    y = 10
    
    # Limitar denominación a 40 caracteres totales (37 + "...")
    detalle_truncado = detalle_bien[:37] + "..." if len(detalle_bien) > 40 else detalle_bien
    
    # Denominación del bien (compacta, hasta 2 líneas)
    denominacion_lines = wrap_text(draw, detalle_truncado, font_title, max_text_width)[:2]
    for line in denominacion_lines:
        draw.text((margin_left, y), line, fill="black", font=font_title)
        y += int(font_title.size * 1.1)
    
    # Título Inventario (NEGRO PURO - antes era gris)
    detalle_linea = title.upper() if title else ""
    draw.text((margin_left, y), detalle_linea, fill="black", font=font_detalle)
    y += int(font_detalle.size * 1.15)
    
    # ÁREA / OFICINA (visible y claro)
    draw.text((margin_left, y), "ÁREA / OFICINA: __________________________________", fill="black", font=font_area)
    y += int(font_area.size * 1.2)


    # 5️⃣ Pegar barcode centrado
    # Espacio reservado para: código numérico (35px) + logo/tipo registro (50px)
    espacio_inferior = 85
    espacio_disponible = TARGET_HEIGHT - y - espacio_inferior
    
    # Si el barcode es muy alto, redimensionarlo para que quepa
    if barcode_img.height > espacio_disponible:
        scale = espacio_disponible / barcode_img.height
        new_w = int(barcode_img.width * scale)
        new_h = int(barcode_img.height * scale)
        barcode_img = barcode_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    x = (TARGET_WIDTH - barcode_img.width) // 2
    canvas_img.paste(barcode_img, (x, y))
    y += barcode_img.height + 5
    
    # 6️⃣ Número del código debajo del barcode (centrado)
    font_codigo = get_font(size=38, bold=True)
    codigo_width = draw.textlength(codigo, font=font_codigo)
    draw.text(((TARGET_WIDTH - codigo_width) / 2, y), codigo, fill="black", font=font_codigo)

    # 7️⃣ Agregar logo (esquina inferior izquierda)
    _add_logo(canvas_img, logo_path)

    # Tipo de registro en la esquina inferior derecha
    if tipo_registro:
        font_tipo = get_font(size=40, bold=True)
        text_w = draw.textlength(tipo_registro, font=font_tipo)
        x_tipo = TARGET_WIDTH - text_w - 20
        y_tipo = TARGET_HEIGHT - font_tipo.size - 15
        draw.text((x_tipo, y_tipo), tipo_registro, fill="black", font=font_tipo)

    # 7️⃣ Guardar en memoria, NO en disco
    if not save_file:
        buffer = BytesIO()
        canvas_img.save(buffer, format="PNG", dpi=(DPI, DPI))
        buffer.seek(0)
        return ImageReader(buffer)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    file_path = os.path.join(OUTPUT_DIR, f"{codigo}.png")
    canvas_img.save(file_path, dpi=(DPI, DPI))
    return file_path


def get_font(size: int = 25, bold: bool = False) -> ImageFont.FreeTypeFont:
    """
    Retorna una fuente TrueType compatible según el sistema operativo.
    Si no encuentra ninguna, devuelve una fuente por defecto.
    """

    system = platform.system()

    font_map = {
        "Windows": {
            False: "arial.ttf",
            True: "arialbd.ttf"
        },
        "Linux": {
            False: "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            True: "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        },
        "Darwin": {  # macOS
            False: "/System/Library/Fonts/SFNS.ttf",
            True: "/System/Library/Fonts/SFNSRounded-Bold.ttf"
        }
    }

    # Obtener ruta según OS, si el sistema no está usar Linux como fallback
    paths = font_map.get(system, font_map["Linux"])
    font_path = paths[bold]

    try:
        return ImageFont.truetype(font_path, size)
    except OSError:
        print(
            f"⚠️ No se encontró la fuente: {font_path}, usando fuente por defecto.")
        return ImageFont.load_default()


def _generate_separator_image(office_name: str):
    img, draw = _create_canvas()
    
    # Obtener la clave de 4 letras
    office_key = get_office_key(office_name)
    
    # Draw a thick border or filled background to distinguish
    draw.rectangle(
        [MARGIN, MARGIN, TARGET_WIDTH - MARGIN, TARGET_HEIGHT - MARGIN], 
        outline="black", 
        width=20
    )
    
    font_office = get_font(size=70, bold=True)
    font_key = get_font(size=100, bold=True)
    
    # Dibujar la clave grande primero
    key_width = draw.textlength(office_key, font=font_key)
    key_x = (TARGET_WIDTH - key_width) / 2
    key_y = TARGET_HEIGHT * 0.15
    draw.text((key_x, key_y), office_key, fill="black", font=font_key)
    
    # Línea divisoria
    line_y = key_y + font_key.size + 20
    draw.line([MARGIN + 50, line_y, TARGET_WIDTH - MARGIN - 50, line_y], fill="black", width=3)
    
    # Wrap text if too long para el nombre del área
    lines = wrap_text(draw, f"ÁREA: {office_name}", font_office, TARGET_WIDTH * 0.8)
    
    # Calculate starting y position (debajo de la línea)
    start_y = line_y + 20
    
    y = start_y
    for line in lines:
        y = _draw_centered_text(draw, line, y, font_office)
        
    buffer = BytesIO()
    img.save(buffer, format="PNG", dpi=(DPI, DPI))
    buffer.seek(0)
    return ImageReader(buffer)


def generate_barcodes_pdf(records, output_pdf="assets/generated_barcodes/", progress_callback=None, selected_office=""):

    output_pdf += "codigos_barras_"+selected_office+".pdf"

    os.makedirs(os.path.dirname(output_pdf), exist_ok=True)

    pdf = canvas.Canvas(output_pdf, pagesize=landscape(A4))
    page_width, page_height = landscape(A4)

    cm = 28.35
    label_width = page_width / 5
    label_height = page_height / 7

    cols = 5
    rows = 7

    # 🟡 MARGEN SEGURO DE IMPRESIÓN (ajusta si hace falta)
    PAGE_MARGIN_X = cm * 0.5  # 0.5 cm a los lados
    PAGE_MARGIN_Y = cm * 0.5  # 0.5 cm arriba/abajo

    # 🟡 ESPACIADO ENTRE ETIQUETAS
    GAP_X = 6  # espacio horizontal en puntos (≈ 2mm)
    GAP_Y = 6  # espacio vertical en puntos  (≈ 2mm)

    # Área imprimible quitando márgenes externos
    usable_w = page_width - (PAGE_MARGIN_X * 2)
    usable_h = page_height - (PAGE_MARGIN_Y * 2)

    # Ajustar tamaño de cada etiqueta considerando los gaps
    label_width = (usable_w - (GAP_X * (cols - 1))) / cols
    label_height = (usable_h - (GAP_Y * (rows - 1))) / rows

    # Inicio de coordenadas con margen
    x_start = PAGE_MARGIN_X
    y_start = page_height - PAGE_MARGIN_Y - label_height
    x, y = x_start, y_start

    pdf.setStrokeGray(0.6)
    pdf.setLineWidth(0.8)
    pdf.setDash(3, 2)

    def draw_border_cut_lines():
        """Dibuja las líneas de corte en los bordes de la página."""
        # Configurar estilo de línea punteada
        pdf.setStrokeGray(0.6)
        pdf.setLineWidth(0.8)
        pdf.setDash(3, 2)
        
        # Línea SUPERIOR (borde superior de la primera fila)
        top_y = page_height - PAGE_MARGIN_Y
        pdf.line(PAGE_MARGIN_X, top_y, page_width - PAGE_MARGIN_X, top_y)
        
        # Línea INFERIOR (borde inferior de la última fila)
        bottom_y = PAGE_MARGIN_Y
        pdf.line(PAGE_MARGIN_X, bottom_y, page_width - PAGE_MARGIN_X, bottom_y)
        
        # Línea IZQUIERDA (borde izquierdo de la primera columna)
        pdf.line(PAGE_MARGIN_X, PAGE_MARGIN_Y, PAGE_MARGIN_X, page_height - PAGE_MARGIN_Y)
        
        # Línea DERECHA (borde derecho de la última columna)
        pdf.line(page_width - PAGE_MARGIN_X, PAGE_MARGIN_Y, page_width - PAGE_MARGIN_X, page_height - PAGE_MARGIN_Y)
        
        # Líneas HORIZONTALES entre todas las filas
        for row in range(1, rows):
            line_y = page_height - PAGE_MARGIN_Y - (row * (label_height + GAP_Y)) + GAP_Y / 2
            pdf.line(PAGE_MARGIN_X, line_y, page_width - PAGE_MARGIN_X, line_y)
        
        # Líneas VERTICALES entre todas las columnas
        for col in range(1, cols):
            line_x = PAGE_MARGIN_X + (col * (label_width + GAP_X)) - GAP_X / 2
            pdf.line(line_x, PAGE_MARGIN_Y, line_x, page_height - PAGE_MARGIN_Y)

    # Dibujar líneas de corte en la primera página
    draw_border_cut_lines()

    # Pre-process records to insert separators
    processed_items = []
    last_office = None
    
    for record in records:
        # Unpack record
        if len(record) == 4:
             codigo, detalle_bien, tipo_registro, oficina = record
        else:
             # Fallback
             codigo, detalle_bien, tipo_registro = record
             oficina = "DESCONOCIDO"

        # Insert separator if office changes or it's the first one
        if last_office != oficina:
            processed_items.append({"type": "separator", "office": oficina})
        
        processed_items.append({
            "type": "barcode",
            "codigo": codigo,
            "detalle_bien": detalle_bien,
            "tipo_registro": tipo_registro,
            "oficina": oficina
        })
        last_office = oficina

    for i, item in enumerate(processed_items, 1):
        if item["type"] == "separator":
            img = _generate_separator_image(item["office"])
        else:
            img = generate_barcode(
                f"{item['codigo']}",
                title="INVENTARIO DRE HUÁNUCO - 2025",
                detalle_bien=item['detalle_bien'],
                logo_path="utils/logo.png",
                tipo_registro=item['tipo_registro'],
                oficina=item['oficina']
            )

        # Dibujar la etiqueta
        pdf.drawImage(img, x, y, width=label_width, height=label_height)

        if progress_callback:
            progress_callback(i, len(processed_items))

        # Avance de columna
        x += label_width + GAP_X

        # Salto de fila
        if i % cols == 0:
            x = x_start
            y -= label_height + GAP_Y

        # Nueva página
        if i % (cols * rows) == 0 and i < len(processed_items):
            pdf.showPage()
            draw_border_cut_lines()
            x, y = x_start, page_height - PAGE_MARGIN_Y - label_height

    pdf.save()
    return output_pdf


def wrap_text(draw, text, font, max_width):
    """Divide el texto en múltiples líneas sin que exceda el ancho máximo."""
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test_line = f"{current} {word}".strip()
        width = draw.textlength(test_line, font=font)
        if width <= max_width:
            current = test_line
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    return lines
