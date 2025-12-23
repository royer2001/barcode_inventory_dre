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

# Dimensiones mínimas recomendadas para códigos de barras (mm)
# Basado en estándares EAN-13/Code128: 37.29mm x 22.85mm (nominal)
MIN_BARCODE_WIDTH_MM = 37.0
MIN_BARCODE_HEIGHT_MM = 23.0
# Convertir a píxeles a 600 DPI
MIN_BARCODE_WIDTH_PX = int(MIN_BARCODE_WIDTH_MM * CM_TO_INCH * DPI / 10)
MIN_BARCODE_HEIGHT_PX = int(MIN_BARCODE_HEIGHT_MM * CM_TO_INCH * DPI / 10)
# -------------------------------------------------


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


def generate_barcode(codigo: str, title: str = "", logo_path: str = "utils/logo.png", detalle_bien: str = "", save_file: bool = False, tipo_registro: str = ""):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1️⃣ Lienzo base
    canvas_img, draw = _create_canvas()

    # 2️⃣ Generar barcode
    barcode_img = _resize_barcode(_generate_base_barcode(codigo))

    # 3️⃣ Fuentes más grandes para mejor legibilidad
    font_title = get_font(size=42, bold=True)  # Denominación del bien
    font_detalle = get_font(size=34)  # Título inventario
    font_area = get_font(size=38)  # Área / Oficina

    # Margen izquierdo para alineación
    margin_left = 25
    max_text_width = TARGET_WIDTH - margin_left - 25  # Ancho disponible para texto
    
    # 4️⃣ Dibujar textos alineados a la izquierda
    y = 10
    
    # Denominación del bien (compacta, hasta 2 líneas)
    denominacion_lines = wrap_text(draw, detalle_bien, font_title, max_text_width)[:2]
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
    
    # Draw a thick border or filled background to distinguish
    draw.rectangle(
        [MARGIN, MARGIN, TARGET_WIDTH - MARGIN, TARGET_HEIGHT - MARGIN], 
        outline="black", 
        width=20
    )
    
    font_office = get_font(size=70, bold=True)
    
    # Wrap text if too long
    lines = wrap_text(draw, f"ÁREA:\n{office_name}", font_office, TARGET_WIDTH * 0.8)
    
    # Calculate total height of text block
    total_text_height = len(lines) * font_office.size * 1.2
    start_y = (TARGET_HEIGHT - total_text_height) / 2
    
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
                tipo_registro=item['tipo_registro']
            )

        # Dibujar la etiqueta
        pdf.drawImage(img, x, y, width=label_width, height=label_height)

        # --- LÍNEAS DE CORTE PUNTEADAS ---

        # Línea VERTICAL derecha (entre columnas)
        col_actual = (i - 1) % cols + 1
        if col_actual < cols:  # No dibujar después de la última columna
            line_x = x + label_width + GAP_X / 2
            pdf.line(line_x, y, line_x, y + label_height)

        # Línea HORIZONTAL inferior (entre filas)
        row_actual = ((i - 1) // cols) % rows + 1
        # No dibujar en última fila
        if row_actual < rows and i + cols <= len(processed_items):
            line_y = y - GAP_Y / 2
            pdf.line(x, line_y, x + label_width, line_y)

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
            pdf.setStrokeGray(0.6)
            pdf.setLineWidth(0.8)
            pdf.setDash(3, 2)
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
