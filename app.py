import streamlit as st
import pandas as pd
import io
from datetime import datetime

# Configuración de la aplicación en Streamlit
st.set_page_config(page_title="Planificación de Pedidos", layout="wide")
st.title("📦 Generador de Planificación de Pedidos")

# Subir archivo Excel
archivo = st.file_uploader("📥 Sube tu archivo de planificación", type=["xlsx"])

if archivo is not None:
    df = pd.read_excel(archivo)

    # 🔹 Normalizar nombres de columnas
    df.columns = df.columns.str.strip().str.lower()

    # 🔹 Asegurar que las columnas necesarias existen
    columnas_necesarias = ["articulo", "cajaspalet", "pedido", "cajascapas"]
    for col in columnas_necesarias:
        if col not in df.columns:
            st.error(f"❌ Error: Falta la columna requerida '{col}' en el archivo.")
            st.stop()

    # 🔹 Convertir columnas a tipo numérico (manejar errores y NaN)
    for col in ["pedido", "cajaspalet", "cajascapas"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(1)

    # 🔹 Evitar división por cero en `cajaspalet`
    df["cajaspalet"] = df["cajaspalet"].replace(0, 1)

    # 📌 Calcular Pallets Pedido Original
    df["Pallets Pedido (Original)"] = (df["pedido"] / df["cajaspalet"]).round(2)

    # 📌 Ajuste de Pedido Adicional (múltiplo de 33 pallets)
    total_pallets = round(df["Pallets Pedido (Original)"].sum())
    falta_para_33 = (33 - (total_pallets % 33)) % 33

    df["Pedido Adicional"] = 0
    df["Pallets Pedido Adicional"] = 0

    if falta_para_33 > 0:
        top_articulos = df.sort_values(by="pedido", ascending=False).head(3).index
        pedido_por_articulo = ((falta_para_33 / 3) * df.loc[top_articulos, "cajaspalet"]).round().astype(int)
        pedido_por_articulo = (pedido_por_articulo // df.loc[top_articulos, "cajaspalet"]) * df.loc[top_articulos, "cajaspalet"]
        df.loc[top_articulos, "Pedido Adicional"] = pedido_por_articulo
        df["Pallets Pedido Adicional"] = (df["Pedido Adicional"] / df["cajaspalet"]).round(2)

    df["Pallets Pedido Total"] = df["Pallets Pedido (Original)"] + df["Pallets Pedido Adicional"]
    df["Pedido Completo SAP"] = df["pedido"] + df["Pedido Adicional"]

    # 📌 Ajuste de pallets completos para optimizar almacenamiento
    def ajustar_pedido(row):
        pedido_original = row["Pedido Completo SAP"]
        ajuste = 0

        if 0 < (pedido_original % row["cajaspalet"]) <= row["cajascapas"]:
            ajuste = - (pedido_original % row["cajaspalet"])
        elif row["cajaspalet"] - (pedido_original % row["cajaspalet"]) <= row["cajascapas"]:
            ajuste = row["cajaspalet"] - (pedido_original % row["cajaspalet"])

        return ajuste

    df["Ajuste Pedido"] = df.apply(ajustar_pedido, axis=1)
    df["Pedido Final Ajustado"] = df["Pedido Completo SAP"] + df["Ajuste Pedido"]
    df["Pallets Pedido Final"] = df["Pedido Final Ajustado"] / df["cajaspalet"]

    # 📌 Crear los DataFrames finales
    df_pedido_sap = df[(df["Pedido Final Ajustado"] > 0)][
        ["articulo", "descripción de artículo", "pedido", "Pallets Pedido (Original)", "Pedido Adicional",
         "Pallets Pedido Adicional", "cajaspalet", "Pallets Pedido Total", "Pedido Completo SAP",
         "Ajuste Pedido", "Pedido Final Ajustado", "Pallets Pedido Final"]
    ]

    df_errores = df[df["cajascapas"] == 0][["pedido", "cajascapas", "cajaspalet"]]
    df_descatalogar = df[(df["21 días"] < 5) | (df["21 días"] == 0)]

    # 📌 Guardar archivos en memoria para descarga
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_files = {
        f"Planificacion_Pedidos_{timestamp}.xlsx": io.BytesIO(),
        f"Errores_CajasCapas_{timestamp}.xlsx": io.BytesIO(),
        f"Productos_Para_Descatalogar_{timestamp}.xlsx": io.BytesIO(),
        f"Pedido_para_SAP_{timestamp}.xlsx": io.BytesIO(),
    }

    df.to_excel(output_files[f"Planificacion_Pedidos_{timestamp}.xlsx"], index=False, engine='xlsxwriter')
    df_errores.to_excel(output_files[f"Errores_CajasCapas_{timestamp}.xlsx"], index=False, engine='xlsxwriter')
    df_descatalogar.to_excel(output_files[f"Productos_Para_Descatalogar_{timestamp}.xlsx"], index=False, engine='xlsxwriter')
    df_pedido_sap.to_excel(output_files[f"Pedido_para_SAP_{timestamp}.xlsx"], index=False, engine='xlsxwriter')

    # 📌 Mostrar opción de descarga en Streamlit
    st.success("✅ ¡Archivos generados correctamente!")
    for nombre, archivo in output_files.items():
        archivo.seek(0)
        st.download_button(label=f"📥 Descargar {nombre}", data=archivo, file_name=nombre,
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
