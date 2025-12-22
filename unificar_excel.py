"""
Script para unificar todos los archivos Excel de inventario en un solo archivo.
Combina:
- SIGA Y SOBRANTES.xlsx
- AFECTACION EN USO.xlsx
- PECOSAS.xlsx
- ASIGNACIONES.xlsx
"""

import pandas as pd
from pathlib import Path
from datetime import datetime


def limpiar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia y normaliza los nombres de las columnas."""
    # Renombrar columnas para estandarizar
    columnas_rename = {
        'ITEM ': 'ITEM',
        'CODIGO DEL BIEN': 'CODIGO_BIEN',
        'CODIG\nO DEL BIEN': 'CODIGO_BIEN',
        'CODIGO INTERNO': 'CODIGO_INTERNO',
        'CODIGO INTER. ': 'CODIGO_INTERNO',
        'DETALLE DEL   BIEN': 'DETALLE_BIEN',
        'CARACTERISTICAS': 'CARACTERISTICAS',
        'OFICINA': 'OFICINA',
        'ESTAD.': 'ESTADO',
        'COD. ANT.': 'CODIGO_ANTIGUO',
        'COD.  ANT.': 'CODIGO_ANTIGUO',
        'CANT.': 'CANTIDAD',
        'IMPORTE': 'IMPORTE',
        'RESPONSABLE': 'RESPONSABLE',
        'RESPONSABLE ': 'RESPONSABLE',
        'OBSERVACIÒN ': 'OBSERVACION',
        'OBSERVACIONES ': 'OBSERVACION',
        'CUENTA CONTABLE': 'CUENTA_CONTABLE',
        'N° DE PECOSA': 'NUM_DOCUMENTO',
        'FECHA DE EMISION DE PECOSA': 'FECHA_EMISION',
        'N° PAP. ASIG.': 'NUM_DOCUMENTO',
        'FECHA DE EMISION DE PAP. ASIG.': 'FECHA_EMISION',
        'Unnamed: 2': 'TIPO_REGISTRO',
        'Unnamed: 3': 'TIPO_REGISTRO',
    }
    
    # Aplicar renombrado
    df = df.rename(columns=columnas_rename)
    
    # Eliminar columnas sin nombre (Unnamed) excepto las que renombramos o necesitamos
    columnas_validas = [col for col in df.columns if not col.startswith('Unnamed')]
    df = df[columnas_validas]
    
    return df


def cargar_siga_sobrantes(ruta: Path) -> pd.DataFrame:
    """Carga y procesa el archivo SIGA Y SOBRANTES."""
    df = pd.read_excel(ruta, sheet_name='Hoja1', header=2)
    df = limpiar_columnas(df)
    df['ORIGEN'] = 'SIGA_SOBRANTES'
    df['NUM_DOCUMENTO'] = None
    df['FECHA_EMISION'] = None
    return df


def cargar_afectacion(ruta: Path) -> pd.DataFrame:
    """Carga y procesa el archivo AFECTACION EN USO."""
    df = pd.read_excel(ruta, sheet_name='Hoja1', header=0)
    df = limpiar_columnas(df)
    df['ORIGEN'] = 'AFECTACION_EN_USO'
    df['NUM_DOCUMENTO'] = None
    df['FECHA_EMISION'] = None
    df['CANTIDAD'] = 1  # Asumir cantidad 1 si no existe
    return df


def cargar_pecosas(ruta: Path) -> pd.DataFrame:
    """Carga y procesa el archivo PECOSAS."""
    df = pd.read_excel(ruta, sheet_name='Hoja1', header=1)
    df = limpiar_columnas(df)
    df['ORIGEN'] = 'PECOSAS'
    return df


def cargar_asignaciones(ruta: Path) -> pd.DataFrame:
    """Carga y procesa el archivo ASIGNACIONES."""
    df = pd.read_excel(ruta, sheet_name='Hoja1', header=1)
    df = limpiar_columnas(df)
    df['ORIGEN'] = 'ASIGNACIONES'
    return df


def unificar_excel(directorio: str = '.', salida: str = None) -> str:
    """
    Unifica todos los archivos Excel en un solo archivo.
    
    Args:
        directorio: Directorio donde están los archivos Excel
        salida: Nombre del archivo de salida (opcional)
    
    Returns:
        Ruta del archivo generado
    """
    directorio = Path(directorio)
    
    # Definir archivos a procesar
    archivos = {
        'SIGA Y SOBRANTES.xlsx': cargar_siga_sobrantes,
        'AFECTACION EN USO.xlsx': cargar_afectacion,
        'PECOSAS.xlsx': cargar_pecosas,
        'ASIGNACIONES.xlsx': cargar_asignaciones,
    }
    
    # Cargar todos los DataFrames
    dataframes = []
    for archivo, funcion_carga in archivos.items():
        ruta = directorio / archivo
        if ruta.exists():
            print(f"✅ Cargando: {archivo}")
            try:
                df = funcion_carga(ruta)
                print(f"   → {len(df)} registros encontrados")
                dataframes.append(df)
            except Exception as e:
                print(f"❌ Error al cargar {archivo}: {e}")
        else:
            print(f"⚠️  Archivo no encontrado: {archivo}")
    
    if not dataframes:
        print("❌ No se encontraron archivos para procesar")
        return None
    
    # Columnas finales deseadas (en orden)
    columnas_finales = [
        'ORIGEN',
        'TIPO_REGISTRO',
        'NUM_DOCUMENTO',
        'FECHA_EMISION',
        'ITEM',
        'CODIGO_BIEN',
        'CODIGO_INTERNO',
        'DETALLE_BIEN',
        'CARACTERISTICAS',
        'OFICINA',
        'ESTADO',
        'CODIGO_ANTIGUO',
        'CANTIDAD',
        'IMPORTE',
        'RESPONSABLE',
        'OBSERVACION',
        'CUENTA_CONTABLE',
    ]
    
    # Asegurar que cada DataFrame tenga todas las columnas
    for i, df in enumerate(dataframes):
        for col in columnas_finales:
            if col not in df.columns:
                df[col] = None
        # Reordenar columnas
        dataframes[i] = df[columnas_finales]
    
    # Concatenar todos los DataFrames
    df_unificado = pd.concat(dataframes, ignore_index=True)
    
    # Convertir IMPORTE a numérico (manejar valores no numéricos)
    df_unificado['IMPORTE'] = pd.to_numeric(df_unificado['IMPORTE'], errors='coerce')
    
    # Generar nombre de archivo de salida
    if salida is None:
        fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
        salida = f'INVENTARIO_UNIFICADO_{fecha}.xlsx'
    
    ruta_salida = directorio / 'excel' / salida
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    
    # Guardar archivo Excel
    print(f"\n📊 Guardando archivo unificado...")
    
    with pd.ExcelWriter(ruta_salida, engine='openpyxl') as writer:
        # Hoja principal con todos los datos
        df_unificado.to_excel(writer, sheet_name='Inventario Completo', index=False)
        
        # Hojas separadas por origen
        for origen in df_unificado['ORIGEN'].unique():
            df_origen = df_unificado[df_unificado['ORIGEN'] == origen]
            nombre_hoja = origen[:31]  # Excel limita a 31 caracteres
            df_origen.to_excel(writer, sheet_name=nombre_hoja, index=False)
        
        # Resumen - contar registros y sumar importes
        resumen_data = []
        for origen in df_unificado['ORIGEN'].unique():
            df_origen = df_unificado[df_unificado['ORIGEN'] == origen]
            resumen_data.append({
                'ORIGEN': origen,
                'TOTAL_REGISTROS': len(df_origen),
                'IMPORTE_TOTAL': df_origen['IMPORTE'].sum()
            })
        resumen = pd.DataFrame(resumen_data)
        resumen.to_excel(writer, sheet_name='Resumen', index=False)
    
    print(f"✅ Archivo guardado: {ruta_salida}")
    print(f"\n📈 RESUMEN:")
    print(f"   Total de registros: {len(df_unificado)}")
    print(f"\n   Desglose por origen:")
    for origen in df_unificado['ORIGEN'].unique():
        count = len(df_unificado[df_unificado['ORIGEN'] == origen])
        print(f"   • {origen}: {count} registros")
    
    return str(ruta_salida)


if __name__ == "__main__":
    print("=" * 60)
    print("  UNIFICACIÓN DE ARCHIVOS EXCEL DE INVENTARIO")
    print("=" * 60)
    print()
    
    ruta_generada = unificar_excel()
    
    if ruta_generada:
        print()
        print("=" * 60)
        print(f"  ✅ Proceso completado exitosamente!")
        print(f"  📁 Archivo: {ruta_generada}")
        print("=" * 60)
