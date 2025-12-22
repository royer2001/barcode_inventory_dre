"""
Script para analizar los registros que no se están insertando en la base de datos.
"""

import pandas as pd
from db.database import create_connection
import os

def analizar_faltantes():
    """
    Compara los registros del Excel con los de la base de datos
    para identificar los que no fueron insertados.
    """
    print("=" * 80)
    print("📊 ANÁLISIS DE REGISTROS FALTANTES")
    print("=" * 80)
    
    # Cargar Excel
    file_path = "SIGA Y SOBRANTES.xlsx"
    sheet_name = "Hoja1"
    header = 2
    
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=header, dtype=str)
    df.columns = [str(c).strip().lower() for c in df.columns]
    
    print(f"\n📁 Archivo: {file_path}")
    print(f"📄 Hoja: {sheet_name}")
    print(f"📊 Total de filas en Excel: {len(df)}")
    
    # Detectar columnas
    col_pat = next((c for c in df.columns if "codigo del bien" in c or "patrimonial" in c), None)
    col_int = next((c for c in df.columns if "codigo interno" in c or "codigo inter" in c), None)
    col_det = next((c for c in df.columns if "detalle del   bien" in c), None)
    col_reg = next((c for c in df.columns if "unnamed: 2" in c or "tipo de registro" in c), None)
    
    print(f"\n🔍 Columnas detectadas:")
    print(f"   - Código patrimonial: {col_pat}")
    print(f"   - Código interno: {col_int}")
    print(f"   - Detalle bien: {col_det}")
    print(f"   - Tipo registro: {col_reg}")
    
    # Análisis de registros
    print("\n" + "=" * 80)
    print("📋 ANÁLISIS DE REGISTROS POR CATEGORÍA")
    print("=" * 80)
    
    # 1. Registros con valores nulos en código patrimonial o interno
    nulos = df[df[col_pat].isna() | df[col_int].isna() | 
               (df[col_pat].astype(str).str.strip() == '') | 
               (df[col_int].astype(str).str.strip() == '') |
               (df[col_pat].astype(str).str.lower() == 'nan') |
               (df[col_int].astype(str).str.lower() == 'nan')]
    print(f"\n1️⃣ Registros con código patrimonial o interno vacío/nulo: {len(nulos)}")
    if not nulos.empty:
        print("   Primeros 5 ejemplos:")
        for idx, row in nulos.head(5).iterrows():
            print(f"      Fila {idx+header+2}: Pat='{row.get(col_pat, '')}', Int='{row.get(col_int, '')}'")
    
    # 2. Registros filtrados por palabras clave
    df_temp = df.dropna(subset=[col_pat, col_int], how="all")
    filtrados = df_temp[df_temp[col_pat].astype(str).str.contains(
        "firma|total|observacion", case=False, na=False)]
    print(f"\n2️⃣ Registros filtrados por 'firma|total|observacion': {len(filtrados)}")
    if not filtrados.empty:
        print("   Primeros 5 ejemplos:")
        for idx, row in filtrados.head(5).iterrows():
            print(f"      Fila {idx+header+2}: {row[col_pat][:60]}...")
    
    # 3. Duplicados internos en el Excel
    df_valid = df.dropna(subset=[col_pat, col_int], how="all")
    df_valid = df_valid[~df_valid[col_pat].astype(str).str.contains(
        "firma|total|observacion", case=False, na=False)]
    
    # Normalizar códigos
    df_valid['cod_pat_norm'] = df_valid[col_pat].astype(str).str.strip()
    df_valid['cod_int_norm'] = df_valid[col_int].astype(str).str.replace('.0', '', regex=False)
    df_valid['cod_int_norm'] = df_valid['cod_int_norm'].str.zfill(4)
    
    # Crear código completo considerando SOBRANTES
    df_valid['tipo_reg'] = df_valid[col_reg].astype(str).str.lower()
    df_valid['is_sobrante'] = df_valid['tipo_reg'].str.contains('sobrantes', na=False)
    df_valid['codigo_completo'] = df_valid['cod_pat_norm'] + df_valid['cod_int_norm']
    df_valid.loc[df_valid['is_sobrante'], 'codigo_completo'] = df_valid.loc[df_valid['is_sobrante'], 'codigo_completo'] + 'S'
    
    duplicados = df_valid[df_valid.duplicated('codigo_completo', keep=False)]
    duplicados_unicos = df_valid[df_valid.duplicated('codigo_completo', keep='first')]
    
    print(f"\n3️⃣ Registros duplicados internos (mismo código completo):")
    print(f"   - Total de registros en grupos duplicados: {len(duplicados)}")
    print(f"   - Registros que serían ignorados por duplicación: {len(duplicados_unicos)}")
    
    if not duplicados.empty:
        # Agrupar duplicados
        dup_counts = df_valid.groupby('codigo_completo').size().reset_index(name='veces')
        dup_counts = dup_counts[dup_counts['veces'] > 1].sort_values('veces', ascending=False)
        
        print(f"\n   🔁 Códigos duplicados encontrados: {len(dup_counts)}")
        print("   Top 10 más repetidos:")
        for _, row in dup_counts.head(10).iterrows():
            codigo = row['codigo_completo']
            veces = row['veces']
            # Buscar detalle
            detalle = df_valid[df_valid['codigo_completo'] == codigo][col_det].iloc[0] if col_det else "N/A"
            detalle = str(detalle)[:50] if detalle else "N/A"
            print(f"      {codigo}: {veces} veces - {detalle}...")
    
    # 4. Registros que pasaron los filtros (deberían insertarse)
    registros_validos = len(df_valid) - len(duplicados_unicos)
    print(f"\n4️⃣ Registros válidos esperados (sin duplicados): {registros_validos}")
    
    # 5. Verificar en la base de datos
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bienes';")
    if cursor.fetchone():
        df_db = pd.read_sql_query("SELECT * FROM bienes", conn)
        print(f"\n5️⃣ Registros en la base de datos: {len(df_db)}")
        
        diferencia = registros_validos - len(df_db)
        print(f"\n📊 DIFERENCIA: {diferencia} registros")
        
        if diferencia != 0:
            print("\n⚠️ Hay una diferencia, analizando...")
            
            # Comparar códigos
            codigos_excel = set(df_valid['codigo_completo'].unique())
            codigos_db = set(df_db['codigo_completo'].unique())
            
            en_excel_no_db = codigos_excel - codigos_db
            print(f"\n   Códigos en Excel pero NO en BD: {len(en_excel_no_db)}")
            if en_excel_no_db:
                for codigo in list(en_excel_no_db)[:10]:
                    detalle = df_valid[df_valid['codigo_completo'] == codigo][col_det].iloc[0] if col_det else "N/A"
                    print(f"      {codigo}: {str(detalle)[:50]}...")
    else:
        print("\n⚠️ La tabla 'bienes' no existe en la base de datos")
    
    conn.close()
    
    # Resumen
    print("\n" + "=" * 80)
    print("📋 RESUMEN DE REGISTROS")
    print("=" * 80)
    total_excel = len(df)
    print(f"   📊 Total en Excel:                    {total_excel}")
    print(f"   ❌ Nulos/vacíos:                      -{len(nulos)}")
    print(f"   ❌ Filtrados (firma/total/obs):       -{len(filtrados)}")
    print(f"   ❌ Duplicados internos:               -{len(duplicados_unicos)}")
    print(f"   ✅ Esperados válidos:                 {registros_validos}")
    
    # Generar reporte de los que faltan
    if not os.path.exists('reportes'):
        os.makedirs('reportes')
    
    with pd.ExcelWriter('reportes/analisis_faltantes.xlsx', engine='openpyxl') as writer:
        if not nulos.empty:
            nulos.to_excel(writer, sheet_name='Nulos_Vacios', index=False)
        if not filtrados.empty:
            filtrados.to_excel(writer, sheet_name='Filtrados', index=False)
        if not duplicados.empty:
            duplicados.to_excel(writer, sheet_name='Duplicados', index=False)
        
        # Resumen de duplicados
        if not duplicados.empty:
            dup_counts.to_excel(writer, sheet_name='Resumen_Duplicados', index=False)
    
    print(f"\n📂 Reporte detallado guardado en: reportes/analisis_faltantes.xlsx")


if __name__ == "__main__":
    analizar_faltantes()
