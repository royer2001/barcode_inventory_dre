from data.load_excel import load_excel_to_db
from ui.app_ui import InventoryApp

if __name__ == "__main__":
    # 1️⃣ Cargar Excel a la base de datos (solo una vez)
    # anexo 01
    # load_excel_to_db("ANEXOS 01 - BIENES Y MUEBLES EN USO - SIGA TOTAL 2024.xlsx",
    #                 sheet_name="1 MUEBLES", header=5, tipo_registro="SIGA")

    # load_excel_to_db("ANEXOS 01 - BIENES Y MUEBLES EN USO - SIGA TOTAL 2024.xlsx",
    #                sheet_name="2 MUEBLES OK ", header=3, tipo_registro="SIGA")

    # anexo 02
    # load_excel_to_db("ANEXOS 02 - MAQUINARIA Y EQUIPO  EN USO - SIGA TOTAL 2024.xlsx",
    #               sheet_name="2 MAQ.", header=5, tipo_registro="SIGA")
    # load_excel_to_db("ANEXOS 02 - MAQUINARIA Y EQUIPO  EN USO - SIGA TOTAL 2024.xlsx",
    #              sheet_name="3. MAQ.", header=3, tipo_registro="SIGA")

    # anexo 03
    # load_excel_to_db("ANEXOS 03 - MUEBLES EN USO - SOBRANTES TOTAL 2024.xlsx",
    #             sheet_name="TOTAL MUBLS", header=5, tipo_registro="SOBRANTE")
    # load_excel_to_db("ANEXOS 03 - MUEBLES EN USO - SOBRANTES TOTAL 2024.xlsx",
    #            sheet_name="MUEBLES TOT", header=0, tipo_registro="SOBRANTE")

    # anexo 04
    # load_excel_to_db("ANEXOS 04- MAQUINARIA - SOBRANTES TOTAL 2024 a.xlsx",
    #           sheet_name="MAQUI.SOBRANTES", header=5, tipo_registro="SOBRANTE")
    # load_excel_to_db("ANEXOS 04- MAQUINARIA - SOBRANTES TOTAL 2024 a.xlsx",
    #          sheet_name="SOBRNT.", header=0, tipo_registro="SOBRANTE")

    load_excel_to_db("excel/INVENTARIO_UNIFICADO_20251217_180210.xlsx", sheet_name="Inventario Completo", header=0)

    # 2️⃣ Ejecutar interfaz
    app = InventoryApp()
    app.mainloop()
