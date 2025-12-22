import sqlite3
import os

# Obtener la ruta del directorio raíz del proyecto
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.path.join(_BASE_DIR, "inventario.db")

def create_connection():
    conn = sqlite3.connect(_DB_PATH)
    return conn

def create_table():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bienes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_patrimonial TEXT,
            codigo_interno TEXT,
            detalle_bien TEXT,
            descripcion TEXT,
            oficina TEXT,
            fuente TEXT,
            tipo_registro TEXT,
            codigo_completo TEXT UNIQUE,
            estado TEXT,
            responsable TEXT
        )
    """)
    conn.commit()
    conn.close()
