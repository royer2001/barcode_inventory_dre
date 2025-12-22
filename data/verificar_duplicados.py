"""
Script para verificar duplicados entre las 3 fuentes de datos:
1. SIGA Y SOBRANTES.xlsx
2. AFECTACION EN USO.xlsx
3. PECOSAS.xlsx
"""

import pandas as pd
from db.database import create_connection
import os

def verificar_duplicados_db():
    """
    Verifica duplicados en la base de datos entre las 3 fuentes.
    """
    conn = create_connection()
    
    # Verificar si la tabla bienes existe
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bienes';")
    if not cursor.fetchone():
        print("=" * 80)
        print("⚠️ LA TABLA 'bienes' NO EXISTE EN LA BASE DE DATOS")
        print("=" * 80)
        print("Por favor, carga los datos primero ejecutando main.py")
        conn.close()
        return {'duplicados_exactos': 0, 'duplicados_patrimonial': 0, 'en_multiples_fuentes': 0}
    
    print("=" * 80)
    print("📊 VERIFICACIÓN DE DUPLICADOS ENTRE LAS 3 FUENTES")
    print("=" * 80)
    
    # 1. Resumen por fuente
    print("\n📁 RESUMEN POR FUENTE:")
    print("-" * 50)
    df_resumen = pd.read_sql_query("""
        SELECT fuente, tipo_registro, COUNT(*) as total 
        FROM bienes 
        GROUP BY fuente, tipo_registro
        ORDER BY fuente
    """, conn)
    print(df_resumen.to_string(index=False))
    
    # 2. Verificar duplicados de codigo_patrimonial + codigo_interno entre fuentes
    print("\n🔍 DUPLICADOS POR CÓDIGO PATRIMONIAL + CÓDIGO INTERNO:")
    print("-" * 50)
    
    # Buscar registros que tengan el mismo codigo_patrimonial y codigo_interno pero diferente fuente
    df_duplicados_fuentes = pd.read_sql_query("""
        SELECT 
            b1.codigo_patrimonial,
            b1.codigo_interno,
            b1.detalle_bien,
            b1.fuente as fuente_1,
            b1.tipo_registro as tipo_1,
            b2.fuente as fuente_2,
            b2.tipo_registro as tipo_2
        FROM bienes b1
        INNER JOIN bienes b2 ON 
            b1.codigo_patrimonial = b2.codigo_patrimonial 
            AND b1.codigo_interno = b2.codigo_interno
            AND b1.id < b2.id
        ORDER BY b1.codigo_patrimonial, b1.codigo_interno
    """, conn)
    
    if df_duplicados_fuentes.empty:
        print("✅ No se encontraron duplicados entre las diferentes fuentes.")
    else:
        print(f"⚠️ Se encontraron {len(df_duplicados_fuentes)} registros duplicados entre fuentes:")
        print(df_duplicados_fuentes.to_string(index=False))
    
    # 3. Verificar duplicados de codigo_patrimonial solo
    print("\n🔍 DUPLICADOS POR CÓDIGO PATRIMONIAL (mismos bienes en distintas fuentes):")
    print("-" * 50)
    
    df_dup_patrimonial = pd.read_sql_query("""
        SELECT 
            codigo_patrimonial,
            GROUP_CONCAT(DISTINCT fuente) as fuentes,
            GROUP_CONCAT(DISTINCT tipo_registro) as tipos,
            COUNT(*) as veces
        FROM bienes
        GROUP BY codigo_patrimonial
        HAVING COUNT(DISTINCT fuente) > 1
        ORDER BY veces DESC
        LIMIT 50
    """, conn)
    
    if df_dup_patrimonial.empty:
        print("✅ No hay bienes que aparezcan en múltiples fuentes (por código patrimonial).")
    else:
        print(f"⚠️ {len(df_dup_patrimonial)} códigos patrimoniales aparecen en múltiples fuentes:")
        print(df_dup_patrimonial.to_string(index=False))
    
    # 4. Verificar duplicados exactos (mismo codigo_completo)
    print("\n🔍 DUPLICADOS POR CÓDIGO COMPLETO (deberían ser 0 por UNIQUE constraint):")
    print("-" * 50)
    
    df_dup_completo = pd.read_sql_query("""
        SELECT 
            codigo_completo,
            COUNT(*) as veces
        FROM bienes
        GROUP BY codigo_completo
        HAVING COUNT(*) > 1
        ORDER BY veces DESC
        LIMIT 20
    """, conn)
    
    if df_dup_completo.empty:
        print("✅ No hay duplicados de código completo (constraint UNIQUE funciona correctamente).")
    else:
        print(f"⚠️ {len(df_dup_completo)} códigos completos duplicados (esto no debería ocurrir):")
        print(df_dup_completo.to_string(index=False))
    
    # 5. Verificar bienes que están en las 3 fuentes
    print("\n🔍 BIENES QUE PODRÍAN ESTAR EN MÚLTIPLES FUENTES (por código patrimonial):")
    print("-" * 50)
    
    df_tres_fuentes = pd.read_sql_query("""
        SELECT 
            codigo_patrimonial,
            detalle_bien,
            GROUP_CONCAT(fuente || ' (' || tipo_registro || ')') as fuentes_tipos,
            GROUP_CONCAT(codigo_interno) as codigos_internos,
            COUNT(*) as total_registros
        FROM bienes
        GROUP BY codigo_patrimonial, detalle_bien
        HAVING COUNT(DISTINCT fuente) >= 2
        ORDER BY total_registros DESC
        LIMIT 30
    """, conn)
    
    if df_tres_fuentes.empty:
        print("✅ No hay bienes que aparezcan en 2 o más fuentes distintas.")
    else:
        print(f"⚠️ {len(df_tres_fuentes)} bienes aparecen en múltiples fuentes:")
        for _, row in df_tres_fuentes.iterrows():
            print(f"\n  📦 Código: {row['codigo_patrimonial']}")
            print(f"     Detalle: {row['detalle_bien'][:60]}...")
            print(f"     Fuentes: {row['fuentes_tipos']}")
            print(f"     Códigos Internos: {row['codigos_internos']}")
            print(f"     Total registros: {row['total_registros']}")
    
    # 6. Generar reporte Excel si hay duplicados
    if not df_duplicados_fuentes.empty or not df_dup_patrimonial.empty or not df_tres_fuentes.empty:
        if not os.path.exists('reportes'):
            os.makedirs('reportes')
        
        report_path = "reportes/duplicados_entre_fuentes.xlsx"
        with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
            # Resumen
            df_resumen.to_excel(writer, sheet_name='Resumen por Fuente', index=False)
            
            # Duplicados entre fuentes
            if not df_duplicados_fuentes.empty:
                df_duplicados_fuentes.to_excel(writer, sheet_name='Duplicados Exactos', index=False)
            
            # Duplicados por código patrimonial
            if not df_dup_patrimonial.empty:
                df_dup_patrimonial.to_excel(writer, sheet_name='Por Cod Patrimonial', index=False)
            
            # Bienes en múltiples fuentes
            if not df_tres_fuentes.empty:
                df_tres_fuentes.to_excel(writer, sheet_name='Multiples Fuentes', index=False)
        
        print(f"\n📂 Reporte generado: {report_path}")
    
    # 7. Estadísticas finales
    print("\n" + "=" * 80)
    print("📈 ESTADÍSTICAS FINALES")
    print("=" * 80)
    
    total = pd.read_sql_query("SELECT COUNT(*) as total FROM bienes", conn).iloc[0]['total']
    print(f"📊 Total de registros en la base de datos: {total}")
    
    fuentes = pd.read_sql_query("SELECT COUNT(DISTINCT fuente) as total FROM bienes", conn).iloc[0]['total']
    print(f"📁 Número de fuentes diferentes: {fuentes}")
    
    patrimoniales_unicos = pd.read_sql_query("SELECT COUNT(DISTINCT codigo_patrimonial) as total FROM bienes", conn).iloc[0]['total']
    print(f"🏷️  Códigos patrimoniales únicos: {patrimoniales_unicos}")
    
    conn.close()
    
    return {
        'duplicados_exactos': len(df_duplicados_fuentes),
        'duplicados_patrimonial': len(df_dup_patrimonial),
        'en_multiples_fuentes': len(df_tres_fuentes) if not df_tres_fuentes.empty else 0
    }


def verificar_duplicados_excel():
    """
    Verifica duplicados directamente en los archivos Excel antes de cargar.
    Retorna un DataFrame con los duplicados encontrados.
    """
    print("=" * 80)
    print("📊 VERIFICACIÓN DE DUPLICADOS EN ARCHIVOS EXCEL (PRE-CARGA)")
    print("=" * 80)
    
    archivos = [
        ("SIGA Y SOBRANTES.xlsx", "Hoja1", 2),
        ("AFECTACION EN USO.xlsx", "Hoja1", 0),
        ("PECOSAS.xlsx", "Hoja1", 1)
    ]
    
    all_data = []
    all_data_full = []  # Con todas las columnas para el reporte
    
    for file_path, sheet_name, header in archivos:
        if not os.path.exists(file_path):
            print(f"⚠️ Archivo no encontrado: {file_path}")
            continue
            
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=header, dtype=str)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Detectar columnas
        col_pat = next((c for c in df.columns if "codigo del bien" in c or "patrimonial" in c), None)
        col_int = next((c for c in df.columns if "codigo interno" in c or "codigo inter" in c), None)
        col_det = next((c for c in df.columns if "detalle del   bien" in c or "detalle" in c), None)
        col_ofi = next((c for c in df.columns if "oficina" in c), None)
        col_resp = next((c for c in df.columns if "responsable" in c), None)
        
        if col_pat and col_int:
            # DataFrame simplificado para verificación
            df_temp = df[[col_pat, col_int]].copy()
            df_temp.columns = ['codigo_patrimonial', 'codigo_interno']
            df_temp['fuente'] = file_path
            df_temp = df_temp.dropna(subset=['codigo_patrimonial', 'codigo_interno'], how='all')
            all_data.append(df_temp)
            
            # DataFrame completo para el reporte
            cols_to_keep = [col_pat, col_int]
            col_names = ['codigo_patrimonial', 'codigo_interno']
            
            if col_det:
                cols_to_keep.append(col_det)
                col_names.append('detalle_bien')
            if col_ofi:
                cols_to_keep.append(col_ofi)
                col_names.append('oficina')
            if col_resp:
                cols_to_keep.append(col_resp)
                col_names.append('responsable')
                
            df_full = df[cols_to_keep].copy()
            df_full.columns = col_names
            df_full['archivo_origen'] = file_path
            df_full = df_full.dropna(subset=['codigo_patrimonial', 'codigo_interno'], how='all')
            all_data_full.append(df_full)
            
            print(f"✅ {file_path}: {len(df_temp)} registros encontrados")
        else:
            print(f"⚠️ {file_path}: No se encontraron columnas de código")
    
    duplicados_df = pd.DataFrame()
    resumen_df = pd.DataFrame()
    
    if all_data:
        df_all = pd.concat(all_data, ignore_index=True)
        df_all_full = pd.concat(all_data_full, ignore_index=True)
        
        # Limpiar y normalizar
        df_all['codigo_patrimonial'] = df_all['codigo_patrimonial'].astype(str).str.strip()
        df_all['codigo_interno'] = df_all['codigo_interno'].astype(str).str.replace('.0', '', regex=False)
        df_all['codigo_interno'] = df_all['codigo_interno'].str.zfill(4)
        df_all['key'] = df_all['codigo_patrimonial'] + df_all['codigo_interno']
        
        df_all_full['codigo_patrimonial'] = df_all_full['codigo_patrimonial'].astype(str).str.strip()
        df_all_full['codigo_interno'] = df_all_full['codigo_interno'].astype(str).str.replace('.0', '', regex=False)
        df_all_full['codigo_interno'] = df_all_full['codigo_interno'].str.zfill(4)
        df_all_full['codigo_completo'] = df_all_full['codigo_patrimonial'] + df_all_full['codigo_interno']
        
        # Buscar duplicados entre fuentes
        duplicados = df_all.groupby('key').filter(lambda x: x['fuente'].nunique() > 1)
        
        if duplicados.empty:
            print("\n✅ No hay duplicados entre las fuentes de Excel.")
        else:
            print(f"\n⚠️ {len(duplicados)} registros aparecen en múltiples fuentes:")
            
            # Resumen de duplicados
            resumen_df = duplicados.groupby('key').agg({
                'codigo_patrimonial': 'first',
                'codigo_interno': 'first',
                'fuente': lambda x: ', '.join(sorted(x.unique()))
            }).reset_index()
            resumen_df.columns = ['codigo_completo', 'codigo_patrimonial', 'codigo_interno', 'fuentes_duplicadas']
            
            print(resumen_df.to_string(index=False))
            
            # Obtener registros completos de los duplicados
            keys_duplicados = duplicados['key'].unique()
            duplicados_df = df_all_full[df_all_full['codigo_completo'].isin(keys_duplicados)].copy()
            duplicados_df = duplicados_df.sort_values(['codigo_completo', 'archivo_origen'])
    
    return duplicados_df, resumen_df


def generar_reporte_duplicados():
    """
    Genera un reporte Excel con todos los duplicados encontrados.
    """
    print("\n" + "=" * 80)
    print("📄 GENERANDO REPORTE DE DUPLICADOS")
    print("=" * 80)
    
    # Verificar duplicados en Excel
    duplicados_excel, resumen_excel = verificar_duplicados_excel()
    
    # Crear directorio de reportes si no existe
    if not os.path.exists('reportes'):
        os.makedirs('reportes')
    
    report_path = "reportes/duplicados_entre_fuentes.xlsx"
    
    with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
        # Hoja 1: Resumen de duplicados
        if not resumen_excel.empty:
            resumen_excel.to_excel(writer, sheet_name='Resumen Duplicados', index=False)
            print(f"  ✅ Hoja 'Resumen Duplicados': {len(resumen_excel)} códigos duplicados")
        else:
            pd.DataFrame({'mensaje': ['No se encontraron duplicados entre las fuentes']}).to_excel(
                writer, sheet_name='Resumen Duplicados', index=False)
        
        # Hoja 2: Detalle completo de duplicados
        if not duplicados_excel.empty:
            duplicados_excel.to_excel(writer, sheet_name='Detalle Duplicados', index=False)
            print(f"  ✅ Hoja 'Detalle Duplicados': {len(duplicados_excel)} registros")
        
        # Hoja 3: Duplicados por fuente
        if not duplicados_excel.empty:
            for fuente in duplicados_excel['archivo_origen'].unique():
                nombre_hoja = fuente.replace('.xlsx', '').replace(' ', '_')[:31]
                df_fuente = duplicados_excel[duplicados_excel['archivo_origen'] == fuente]
                df_fuente.to_excel(writer, sheet_name=nombre_hoja, index=False)
                print(f"  ✅ Hoja '{nombre_hoja}': {len(df_fuente)} registros duplicados")
    
    print(f"\n📂 Reporte generado: {report_path}")
    return report_path


if __name__ == "__main__":
    print("\n" + "🔄" * 40)
    print("INICIANDO VERIFICACIÓN DE DUPLICADOS ENTRE LAS 3 FUENTES")
    print("🔄" * 40 + "\n")
    
    # Generar reporte de duplicados en Excel
    report_path = generar_reporte_duplicados()
    
    # También verificar en la base de datos si existe
    print("\n\n" + "=" * 80)
    print("📊 VERIFICACIÓN EN BASE DE DATOS")
    print("=" * 80)
    resultado = verificar_duplicados_db()
    
    print("\n\n" + "=" * 80)
    print("📋 RESUMEN FINAL")
    print("=" * 80)
    print(f"  📁 Reporte Excel generado: {report_path}")
    print(f"  • Duplicados en archivos Excel: ver reporte")
    print(f"  • Duplicados en BD (exactos): {resultado['duplicados_exactos']}")
    print(f"  • Códigos patrimoniales en múltiples fuentes (BD): {resultado['duplicados_patrimonial']}")
