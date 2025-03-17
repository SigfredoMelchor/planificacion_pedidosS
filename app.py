import streamlit as st
import pandas as pd
import io
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Planificación de Pedidos", layout="wide")

# Título de la aplicación
st.title("📦 Generador de Planificación de Pedidos")

# Subir archivo Excel
archivo = st.file_uploader("📥 Sube tu archivo de planificación", type=["xlsx"])

if archivo is not None:
    df = pd.read_excel(archivo)
    df.columns = df.columns.str.strip().str.lower()

    # Mapeo de nombres de columnas equivalentes
    nombres_columnas = {
        "articulo": ["articulo", "código de artículo", "id"],
        "descripción de artículo": ["descripción de artículo", "nombre del producto"],
        "21 días": ["21 días", "21_dias", "21dias"],
        "stock virtual": ["stock virtual", "stock_virtual", "stockvirtual"],
        "cajascapas": ["cajascapas", "cajas capas", "cajas_capas"],
        "cajaspalet": ["cajaspalet", "cajas palet", "cajas_palet"],
        "pedido": ["pedido", "orden", "cantidad pedida"]
    }
    
    for key, posibles_nombres in nombres_columnas.items():
        for nombre in posibles_nombres:
            if nombre in df.columns:
                df.rename(columns={nombre: key}, inplace=True)
                break

    # Verificación de columnas necesarias
    columnas_requeridas = list(nombres_columnas.keys())
    columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]

    if columnas_faltantes:
        st.error(f"❌ Error: Faltan las siguientes columnas en el archivo: {', '.join(columnas_faltantes)}")
        st.stop()

    df["cajascapas"] = df["cajascapas"].replace(0, 1)

    # Selección de parámetros
    dias_stock = st.slider("📆 Selecciona los días de stock", 1, 90, 21)
    num_articulos_pedido_adicional = st.slider("📌 Número de artículos para distribuir el pedido adicional", 1, 20, 10)

    if st.button("🚀 Generar Pedido"):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")

        # Procesamiento del pedido
        df["Stock Necesario"] = (df["21 días"] / 21 * dias_stock).round().astype(int)
        df["Exceso de Stock"] = (df["stock virtual"] - df["Stock Necesario"]).round().astype(int)
        df["Pedido Ajustado"] = df.apply(lambda row: max(row["Stock Necesario"] - row["stock virtual"], 0), axis=1)
        df["Pedido Ajustado"] = df.apply(lambda row: ((row["Pedido Ajustado"] // row["cajascapas"]) * row["cajascapas"]) if row["Pedido Ajustado"] > 0 else 0, axis=1)
        
        df["pedido"] = df["Pedido Ajustado"]
        df["Pallets Pedido (Original)"] = (df["pedido"] / df["cajaspalet"]).fillna(0).round(2)

        # Ajuste de pedidos para optimizar el almacenamiento
        def ajustar_pedido(row):
            pedido_original = row["pedido"]
            ajuste = 0
            
            if 0 < (pedido_original % row["cajaspalet"]) <= row["cajascapas"]:
                ajuste = - (pedido_original % row["cajaspalet"])
            elif row["cajaspalet"] - (pedido_original % row["cajaspalet"]) <= row["cajascapas"]:
                ajuste = row["cajaspalet"] - (pedido_original % row["cajaspalet"])
            
            return ajuste
        
        df["Ajuste Pedido"] = df.apply(ajustar_pedido, axis=1)
        df["Pedido Final Ajustado"] = df["pedido"] + df["Ajuste Pedido"]
        df["Pallets Pedido Final"] = df["Pedido Final Ajustado"] / df["cajaspalet"]

        df_pedido_sap = df[(df["Pedido Final Ajustado"] > 0)][
            ["articulo", "descripción de artículo", "pedido", "Pallets Pedido (Original)", "cajaspalet",
             "Ajuste Pedido", "Pedido Final Ajustado", "Pallets Pedido Final"]
        ]

        output_files = {}
        output_files[f"Pedido_para_SAP_{timestamp}"] = io.BytesIO()
        df_pedido_sap.to_excel(output_files[f"Pedido_para_SAP_{timestamp}"], index=False, engine='xlsxwriter')
        output_files[f"Pedido_para_SAP_{timestamp}"].seek(0)

        st.success("✅ ¡Archivos generados correctamente!")
        for nombre, archivo in output_files.items():
            st.download_button(f"📥 Descargar {nombre}", archivo, f"{nombre}.xlsx")
