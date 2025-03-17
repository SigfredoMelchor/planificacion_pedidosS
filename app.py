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

    # 🔹 **Normalizar nombres de columnas**
    df.columns = df.columns.str.strip().str.lower()

    # Mapeo de nombres de columnas equivalentes
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

    # Verificar columnas requeridas
    columnas_requeridas = ["articulo", "descripción de artículo", "21 días", "stock virtual", "cajascapas", "cajaspalet", "pedido"]
    columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if columnas_faltantes:
        st.error(f"❌ Error: Faltan las siguientes columnas en el archivo: {', '.join(columnas_faltantes)}")
        st.stop()

    # Evitar división por cero y NaN en columnas numéricas
    df["cajascapas"] = df["cajascapas"].fillna(1).replace(0, 1).astype(int)
    df["pedido"] = pd.to_numeric(df["pedido"], errors='coerce').fillna(0).astype(int)

    # Selección de parámetros
    dias_stock = st.slider("📆 Selecciona los días de stock", 1, 90, 21)
    num_articulos_pedido_adicional = st.slider("📌 Número de artículos para distribuir el pedido adicional", 1, 20, 10)

    if st.button("🚀 Generar Pedido"):
        # Obtener la fecha y hora actual (sin segundos)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")

        # Filtrar productos con última venta mayor a 3 meses
        if "última venta" in df.columns:
            df["última venta"] = pd.to_datetime(df["última venta"], errors='coerce')
            fecha_limite = datetime.now() - timedelta(days=90)
            df = df[df["última venta"].isna() | (df["última venta"] >= fecha_limite)]

        # Ajustar pedidos en múltiplos de "CajasCapas" para evitar pallets mixtos
        df["Ajuste CajasCapas"] = df["pedido"] % df["cajascapas"]
        df["pedido"] = df["pedido"] - df["Ajuste CajasCapas"]
        
        # Calcular "Pallets Pedido (Original)"
        df["Pallets Pedido (Original)"] = (df["pedido"] / df["cajaspalet"]).fillna(0).round(2)
        
        # 🔹 **Ajustar el Pedido Adicional para que el total de pallets sea múltiplo de 33**
        total_pallets = df["Pallets Pedido (Original)"].sum()
        exceso_pallets = total_pallets % 33
        df["Pedido Adicional"] = 0
        df["Pallets Pedido Adicional"] = 0
        
        if exceso_pallets != 0:
            falta_para_33 = 33 - exceso_pallets
            top_articulos = df.sort_values(by="21 días", ascending=False).head(num_articulos_pedido_adicional).index
            pedido_por_articulo = (falta_para_33 // num_articulos_pedido_adicional) * df.loc[top_articulos, "cajaspalet"]
            df.loc[top_articulos, "Pedido Adicional"] = pedido_por_articulo
            df["Pallets Pedido Adicional"] = (df["Pedido Adicional"] / df["cajaspalet"]).fillna(0).round(2)

        df["Pallets Pedido Total"] = df["Pallets Pedido (Original)"] + df["Pallets Pedido Adicional"]
        df["Pedido Completo SAP"] = df["pedido"] + df["Pedido Adicional"]

        # 📌 Generar los 4 archivos
        output_files = {
            f"Planificacion_Pedidos_{timestamp}.xlsx": df,
            f"Errores_CajasCapas_{timestamp}.xlsx": df[df["cajascapas"] == 0],
            f"Productos_Para_Descatalogar_{timestamp}.xlsx": df[(df["21 días"] < 5) | (df["21 días"] == 0)],
            f"Pedido_para_SAP_{timestamp}.xlsx": df[df["Pedido Completo SAP"] > 0][["articulo", "descripción de artículo", "pedido", "Pallets Pedido (Original)", "Pedido Adicional", "Pallets Pedido Adicional", "cajaspalet", "Pallets Pedido Total", "Pedido Completo SAP", "Ajuste CajasCapas"]]
        }

        # Descargar los archivos
        st.success("✅ ¡Archivos generados correctamente!")
        for nombre, data in output_files.items():
            output_buffer = io.BytesIO()
            data.to_excel(output_buffer, index=False, engine='xlsxwriter')
            output_buffer.seek(0)
            st.download_button(
                label=f"📥 Descargar {nombre}",
                data=output_buffer.getvalue(),
                file_name=nombre,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
else:
    st.warning("📤 **Por favor, sube un archivo Excel para comenzar.**")
