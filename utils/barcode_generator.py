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
DPI = 300
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
LOGO_RATIO_W = 0.15  # Reducido de 0.22
LOGO_RATIO_H = 0.22  # Reducido de 0.32
MAX_BARCODE_WIDTH = TARGET_WIDTH * 0.80
MAX_BARCODE_HEIGHT = TARGET_HEIGHT * 0.35
# -------------------------------------------------


def _create_canvas() -> Tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (TARGET_WIDTH, TARGET_HEIGHT), "white")
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
    writer.module_width = 0.55  # grosor de barras (aumentado para mejor lectura)
    writer.module_height = 20.0  # altura de barras en mm (aumentado)
    writer.write_text = False   # sin texto debajo
    writer.quiet_zone = 6  # margen blanco lateral (mínimo recomendado para Code128)

    Code128(codigo, writer=writer).save(tmp_path)

    img = Image.open(tmp_path + ".png").convert("RGB")
    os.remove(tmp_path + ".png")
    return img


def _resize_barcode(img: Image.Image) -> Image.Image:

    max_w = int(TARGET_WIDTH * 0.95)
    max_h = int(TARGET_HEIGHT * 0.75)  # Aumentado de 0.65 a 0.75 para barras más grandes

    # Redimensionar solo si es más grande que el límite
    if img.width > max_w or img.height > max_h:
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    return img


def _draw_centered_text(draw, text, y, font) -> int:
    text_w = draw.textlength(text, font=font)
    draw.text(((TARGET_WIDTH - text_w) / 2, y), text, fill="black", font=font)
    return y + int(font.size * 1.2)


def _add_logo(canvas: Image.Image, logo_path: str):
    if not os.path.exists(logo_path):
        return

    logo = Image.open(logo_path).convert("RGBA")

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

    # Posición (abajo izquierda con margen)
    x = int(TARGET_WIDTH * 0.05)
    y = int(TARGET_HEIGHT * 0.9) - logo.height

    canvas.paste(logo, (x, y), logo)


def generate_barcode(codigo: str, title: str = "", logo_path: str = "utils/logo.png", detalle_bien: str = "", save_file: bool = False, tipo_registro: str = ""):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1️⃣ Lienzo base
    canvas_img, draw = _create_canvas()

    # 2️⃣ Generar barcode
    barcode_img = _resize_barcode(_generate_base_barcode(codigo))

    # 3️⃣ Fuentes
    font_title = get_font(size=18)  # Reducido de 25 a 18
    font_detalle = get_font(size=23, bold=True)
    font_oficina = get_font(size=18)

    # 4️⃣ Dibujar textos
    y = 20
    y = _draw_centered_text(draw, title, y, font_title)

    lines = wrap_text(draw, detalle_bien, font_detalle, TARGET_WIDTH * 0.9)[:2]
    for line in lines:
        y = _draw_centered_text(draw, line, y, font_detalle)

    y += 10
    y = _draw_centered_text(
        draw, "ÁREA / OFICINA: _______________________________________________", y, font_oficina)
    y += 10

    # 5️⃣ Pegar barcode
    x = (TARGET_WIDTH - barcode_img.width) // 2
    canvas_img.paste(barcode_img, (x, y + 5))

    # 6️⃣ Agregar logo
    _add_logo(canvas_img, logo_path)

    # agregar tipo de registro en la parte inferior derecha
    if tipo_registro:
        font_tipo = get_font(size=20, bold=True)  # Reducido de 32 a 20
        text_w = draw.textlength(tipo_registro, font=font_tipo)
        x_tipo = TARGET_WIDTH - text_w - 20
        y_tipo = TARGET_HEIGHT - font_tipo.size - 20
        draw.text((x_tipo, y_tipo), tipo_registro,
                  fill="black", font=font_tipo)

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
        width=10
    )
    
    font_office = get_font(size=35, bold=True)
    
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

    pdf.setStrokeColorRGB(0.6, 0.6, 0.6)
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
            pdf.setStrokeColorRGB(0.6, 0.6, 0.6)
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
