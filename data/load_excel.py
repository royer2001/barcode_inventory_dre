import pandas as pd
import os
from db.database import create_connection, create_table


def load_excel_to_db(file_path, sheet_name="2 MAQ.", header=None):
    create_table()
    conn = create_connection()
    cursor = conn.cursor()

    # Cargar Excel (fila 6 como encabezado y todo como texto)
    df = pd.read_excel(file_path, sheet_name=sheet_name,
                       header=header, dtype=str)
    df.columns = [str(c).strip().lower() for c in df.columns]

    print("Columnas detectadas:", df.columns.tolist())
    print("Filas totales que pandas está leyendo:", len(df))

    # Detectar columnas principales (soporta formato antiguo y Excel unificado)
    col_pat = next(
        (c for c in df.columns if "codigo del bien" in c or "patrimonial" in c or c == "codigo_bien"), None)
    col_int = next(
        (c for c in df.columns if "codigo interno" in c or "codigo inter" in c or c == "codigo_interno"), None)
    col_det = next(
        (c for c in df.columns if "detalle del   bien" in c or c == "detalle_bien"), None)
    col_desc = next(
        (c for c in df.columns if "caracteristicas" in c or "descripcion" in c), None)
    col_ofi = next((c for c in df.columns if "oficina" in c), None)
    # Para el Excel unificado, usamos la columna 'tipo_registro' como prioridad
    col_reg = next((c for c in df.columns if c == "tipo_registro"), 
              next((c for c in df.columns if "unnamed: 2" in c or "tipo de registro" in c or "unnamed: 3" in c or c == "origen"), None))
    col_est = next((c for c in df.columns if "estad" in c), None)
    col_resp = next((c for c in df.columns if "responsable" in c), None)

    # Mostrar columnas detectadas
    print(f"📋 Mapeo de columnas:")
    print(f"   codigo_patrimonial -> {col_pat}")
    print(f"   codigo_interno     -> {col_int}")
    print(f"   detalle_bien       -> {col_det}")
    print(f"   descripcion        -> {col_desc}")
    print(f"   oficina            -> {col_ofi}")
    print(f"   tipo_registro      -> {col_reg}")
    print(f"   estado             -> {col_est}")
    print(f"   responsable        -> {col_resp}")

    if not all([col_pat, col_int, col_det, col_desc, col_ofi, col_reg]):
        print("❌ No se encontraron las columnas esperadas.")
        print("Columnas detectadas:", df.columns.tolist())
        print("Filas totales que pandas está leyendo:", len(df))
        return

    # Limpiar filas vacías o de firma/total
    df = df.dropna(subset=[col_pat, col_int], how="all")
    df = df[~df[col_pat].astype(str).str.contains(
        "firma|total|observacion", case=False, na=False)]

    # Normalizar codigo interno a 4 dígitos
    df[col_int] = df[col_int].astype(str).str.replace(".0", "", regex=False)
    df[col_int] = df[col_int].str.zfill(4)

    df["key"] = df[col_pat].str.strip() + df[col_int].str.strip()

    # Diferenciar sobrantes en la clave de duplicados para que no se mezclen con SIGA
    is_sobrante = df[col_reg].astype(str).str.lower().str.contains("sobrante", na=False)
    df.loc[is_sobrante, "key"] = df.loc[is_sobrante, "key"] + "S"

    duplicados = df[df.duplicated("key", keep=False)]
    print(f"⚠️ Total de filas duplicadas: {duplicados.shape[0]}")

    resumen = df.groupby("key").size().reset_index(name="veces")
    solo_dup = resumen[resumen["veces"] > 1].sort_values(by="veces", ascending=False)

    print("🔁 Códigos que se repiten y cuántas veces:")
    print(solo_dup.head(20))  # top 20 más repetidos

    print("\nTotal de códigos duplicados únicos:", solo_dup.shape[0])
    print("Total de filas que están en grupos duplicados:", solo_dup["veces"].sum())

    if not os.path.exists('reportes'):
        os.makedirs('reportes')

    valid_data = []
    ignored_data = []

    count = 0
    for _, row in df.iterrows():
        codigo_patrimonial = str(row.get(col_pat, "")).strip()
        codigo_interno = str(row.get(col_int, "")).strip()
        detalle_bien = str(row.get(col_det, "")).strip()
        descripcion = str(row.get(col_desc, "")).strip()
        oficina = str(row.get(col_ofi, "")).strip()
        tipo_registro = str(row.get(col_reg, "")).strip()
        responsable = str(row.get(col_resp, "")).strip()
        
        # Normalizar tipo_registro para Excel unificado y formato antiguo
        tipo_raw = tipo_registro.lower()
        if "sobrante" in tipo_raw:
            tipo_registro = "SOBRANTE"
        elif "siga" in tipo_raw:
            tipo_registro = "SIGA"
        elif "pecosa" in tipo_raw:
            tipo_registro = "PECOSAS"
        elif "asignacion" in tipo_raw:
            tipo_registro = "ASIGNACIONES"
        elif "afectacion" in tipo_raw:
            tipo_registro = "AFECTACION"
        else:
            tipo_registro = tipo_registro.upper()  # Mantener como está
        
        # Procesar estado
        raw_estado = str(row.get(col_est, "")).strip().upper()
        estado_map = {
            'B': 'BUENO',
            'R': 'REGULAR',
            'M': 'MALO',
            'BUENO': 'BUENO',
            'REGULAR': 'REGULAR',
            'MALO': 'MALO'
        }
        
        estado = estado_map.get(raw_estado, 'BUENO')
        if not raw_estado: # Si estaba vacio
             estado = 'BUENO'

        # Corrección del código interno (mantener 4 dígitos)
        if codigo_interno.endswith(".0"):
            codigo_interno = codigo_interno.replace(".0", "")
        if codigo_interno.isdigit():
            codigo_interno = codigo_interno.zfill(4)

        if codigo_patrimonial and codigo_interno:
            codigo_completo = f"{codigo_patrimonial}{codigo_interno}"
            
            # Validación Siga vs Sobrante
            if tipo_registro == "SOBRANTE":
                codigo_completo += "S"

            cursor.execute("""
                INSERT OR IGNORE INTO bienes
                (
                    codigo_patrimonial, 
                    codigo_interno, 
                    detalle_bien, 
                    descripcion, 
                    oficina, 
                    codigo_completo, 
                    fuente, 
                    tipo_registro,
                    estado,
                    responsable
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (codigo_patrimonial,
                  codigo_interno,
                  detalle_bien,
                  descripcion,
                  oficina,
                  codigo_completo,
                  sheet_name,
                  tipo_registro,
                  estado,
                  responsable
                  ))
            if cursor.rowcount > 0:
                count += 1
                # Agregar a lista de válidos (convertir row a dict para guardar)
                row_dict = row.to_dict()
                row_dict['codigo_completo_generado'] = codigo_completo
                valid_data.append(row_dict)
        else:
            ignored_data.append(row.to_dict())

    conn.commit()
    conn.close()
    
    # Consolidar reportes en un solo archivo Excel con múltiples hojas
    report_file_path = "reportes/reporte_consolidado.xlsx"
    with pd.ExcelWriter(report_file_path, engine='xlsxwriter') as writer:
        if valid_data:
            pd.DataFrame(valid_data).to_excel(writer, sheet_name="validos", index=False)
            print("📂 Reporte de válidos generado en la hoja 'validos'.")
        
        if ignored_data:
            pd.DataFrame(ignored_data).to_excel(writer, sheet_name="no considerados", index=False)
            print("📂 Reporte de no considerados generado en la hoja 'no considerados'.")
        
        if not duplicados.empty:
            duplicados.to_excel(writer, sheet_name="duplicados", index=False)
            print("📂 Reporte de duplicados generado en la hoja 'duplicados'.")

        if not solo_dup.empty:
            solo_dup.to_excel(writer, sheet_name="resumen de duplicados", index=False)
            print("📂 Resumen de duplicados generado en la hoja 'resumen de duplicados'.")
            
    print(f"✅ Reporte consolidado guardado en '{report_file_path}'")
    print(f"✅ {count} registros insertados correctamente (con columna Oficina).")
