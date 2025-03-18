import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta

# Configuración de la página
st.set_page_config(page_title="Planificación de Pedidos", layout="wide")

# Título de la aplicación
st.title("📦 Generador de Planificación de Pedidos")

# Subir archivo Excel
archivo = st.file_uploader("📥 Sube tu archivo de planificación", type=["xlsx"])

if archivo is not None:
    df = pd.read_excel(archivo)

    # 🔹 **Corrección: Normalizar nombres de columnas**
    df.columns = df.columns.str.strip().str.lower()  # Convertir a minúsculas y eliminar espacios

    # Mapear nombres de columnas equivalentes
    nombres_columnas = {
        "articulo": ["articulo", "código de artículo", "id"],
        "descripción de artículo": ["descripción de artículo", "nombre del producto"],
        "21 días": ["21 días", "21_dias", "21dias"],
        "stock virtual": ["stock virtual", "stock_virtual", "stockvirtual"],
        "cajascapas": ["cajascapas", "cajas capas", "cajas_capas"],
        "cajaspalet": ["cajaspalet", "cajas palet", "cajas_palet"],
        "pedido": ["pedido", "orden", "cantidad pedida"],
        "última venta": ["última venta", "fecha última venta", "fecha_ultima_venta"]
    }
    
    for key, posibles_nombres in nombres_columnas.items():
        for nombre in posibles_nombres:
            if nombre in df.columns:
                df.rename(columns={nombre: key}, inplace=True)
                break

    # Verificar si todas las columnas necesarias existen
    columnas_requeridas = ["articulo", "descripción de artículo", "21 días", "stock virtual", "cajascapas", "cajaspalet", "pedido"]
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
        
        if "última venta" in df.columns:
            df["última venta"] = pd.to_datetime(df["última venta"], errors='coerce')
            fecha_limite = datetime.now() - timedelta(days=90)
            df = df[df["última venta"].isna() | (df["última venta"] >= fecha_limite)]
        
        df["Stock Necesario"] = (df["21 días"] / 21 * dias_stock).round().astype(int)
        df["Pedido Ajustado"] = df["Stock Necesario"].clip(lower=0)
        df["pedido"] = df["Pedido Ajustado"]
        df["Pallets Pedido (Original)"] = (df["pedido"] / df["cajaspalet"]).fillna(0).round(2)
        
        total_pallets = df["Pallets Pedido (Original)"].sum()
        falta_para_33 = (33 - (total_pallets % 33)) % 33

        df["Pedido Adicional"] = 0
        df["Pallets Pedido Adicional"] = 0
        
        if falta_para_33 > 0:
            top_articulos = df.sort_values(by="21 días", ascending=False).head(num_articulos_pedido_adicional).index
            df.loc[top_articulos, "Pedido Adicional"] = ((falta_para_33 / len(top_articulos)) * df.loc[top_articulos, "cajaspalet"]).round().astype(int)
            df.loc[top_articulos, "Pedido Adicional"] = (df.loc[top_articulos, "Pedido Adicional"] // df.loc[top_articulos, "cajaspalet"]) * df.loc[top_articulos, "cajaspalet"]
            df["Pallets Pedido Adicional"] = (df["Pedido Adicional"] / df["cajaspalet"]).fillna(0).round(2)

        df["Pallets Pedido Total"] = df["Pallets Pedido (Original)"] + df["Pallets Pedido Adicional"]
        df["Pedido Completo SAP"] = df["pedido"] + df["Pedido Adicional"]
        
        output_files = {}
        output_files[f"Planificacion_Pedidos_{timestamp}"] = io.BytesIO()
        df.to_excel(output_files[f"Planificacion_Pedidos_{timestamp}"], index=False, engine='xlsxwriter')
        
        df_errores = df[df["cajascapas"] == 0]
        output_files[f"Errores_CajasCapas_{timestamp}"] = io.BytesIO()
        df_errores.to_excel(output_files[f"Errores_CajasCapas_{timestamp}"], index=False, engine='xlsxwriter')
        
        df_descatalogar = df[(df["21 días"] < 5) | (df["21 días"] == 0)]
        output_files[f"Productos_Para_Descatalogar_{timestamp}"] = io.BytesIO()
        df_descatalogar.to_excel(output_files[f"Productos_Para_Descatalogar_{timestamp}"], index=False, engine='xlsxwriter')
        
        output_files[f"Pedido_para_SAP_{timestamp}"] = io.BytesIO()
        df.to_excel(output_files[f"Pedido_para_SAP_{timestamp}"], index=False, engine='xlsxwriter')
        
        st.success("✅ ¡Archivos generados correctamente!")
        for nombre, archivo in output_files.items():
            st.download_button(
                label=f"📥 Descargar {nombre}",
                data=archivo.getvalue(),
                file_name=f"{nombre}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
else:
    st.warning("📤 **Por favor, sube un archivo Excel para comenzar.**")

     
