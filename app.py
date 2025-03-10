import streamlit as st
import pandas as pd
import io

# Configuración de la página
st.set_page_config(page_title="Planificación de Pedidos", layout="wide")

# Título de la aplicación
st.title("📦 Generador de Planificación de Pedidos")

# Subir archivo Excel
archivo = st.file_uploader("📥 Sube tu archivo de planificación", type=["xlsx"])

if archivo:
    df = pd.read_excel(archivo)
    st.write("📋 **Vista previa del archivo:**")
    st.dataframe(df)

    # Selección de parámetros
    dias_stock = st.slider("📆 Selecciona los días de stock", 1, 90, 21)
    num_articulos_pedido_adicional = st.slider("📌 Número de artículos para distribuir el pedido adicional", 1, 20, 10)

    if st.button("🚀 Generar Pedido"):
        # Procesar el pedido
        df["Stock Necesario"] = (df["21 Días"] / 21 * dias_stock).round().astype(int)
        df["Exceso de Stock"] = (df["Stock Virtual"] - df["Stock Necesario"]).round().astype(int)

        # Calcular "Pedido Ajustado"
        df["Pedido Ajustado"] = df.apply(
            lambda row: max(row["Stock Necesario"] - row["Stock Virtual"], 0) if row["Stock Necesario"] > row["Stock Virtual"] else 0, axis=1
        )

        # Ajustar pedidos en múltiplos de "CajasCapas"
        df["Pedido Ajustado"] = df.apply(
            lambda row: ((row["Pedido Ajustado"] // row["CajasCapas"]) * row["CajasCapas"]) if row["Pedido Ajustado"] > 0 else 0, axis=1
        )

        # Asignar el nuevo pedido calculado
        df["Pedido"] = df["Pedido Ajustado"]
        df["Pallets Pedido"] = (df["Pedido"] / df["CajasPalet"]).fillna(0).round(2)

        # Crear columnas para el archivo "Pedido para SAP"
        df["Pallets Pedido (Original)"] = (df["Pedido"] / df["CajasPalet"]).fillna(0).round(2)
        df["Pedido Completo SAP"] = df["Pedido"]

        # Generar el archivo Excel para descarga
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='xlsxwriter')
        output.seek(0)

        st.success("✅ ¡Pedido generado correctamente!")
        st.dataframe(df)

        st.download_button(
            label="📥 Descargar Pedido en Excel",
            data=output,
            file_name="Planificacion_Pedidos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
