import streamlit as st
import pandas as pd
import io

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

    # Mostrar las columnas detectadas en Streamlit para depuración
    st.write("🔍 **Columnas detectadas en el archivo:**", list(df.columns))

    # 🔹 **Corrección: Mapear nombres de columnas equivalentes**
    nombres_columnas = {
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

    # 🔹 **Verificar si todas las columnas necesarias existen**
    columnas_requeridas = list(nombres_columnas.keys())
    columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]

    if columnas_faltantes:
        st.error(f"❌ Error: Faltan las siguientes columnas en el archivo: {', '.join(columnas_faltantes)}")
        st.stop()

    # Asegurar que "CajasCapas" no sea 0 para evitar división por cero
    df["cajascapas"] = df["cajascapas"].replace(0, 1)

    # Selección de parámetros
    dias_stock = st.slider("📆 Selecciona los días de stock", 1, 90, 21)
    num_articulos_pedido_adicional = st.slider("📌 Número de artículos para distribuir el pedido adicional", 1, 20, 10)

    if st.button("🚀 Generar Pedido"):
        # Procesar el pedido
        df["Stock Necesario"] = (df["21 días"] / 21 * dias_stock).round().astype(int)
        df["Exceso de Stock"] = (df["stock virtual"] - df["Stock Necesario"]).round().astype(int)

        # Calcular "Pedido Ajustado"
        df["Pedido Ajustado"] = df.apply(
            lambda row: max(row["Stock Necesario"] - row["stock virtual"], 0) if row["Stock Necesario"] > row["stock virtual"] else 0, axis=1
        )

        # Ajustar pedidos en múltiplos de "CajasCapas"
        df["Pedido Ajustado"] = df.apply(
            lambda row: ((row["Pedido Ajustado"] // row["cajascapas"]) * row["cajascapas"]) if row["Pedido Ajustado"] > 0 else 0, axis=1
        )

        # Asignar el nuevo pedido calculado
        df["pedido"] = df["Pedido Ajustado"]
        df["Pallets Pedido"] = (df["pedido"] / df["cajaspalet"]).fillna(0).round(2)

        # 🔹 **Generar los cuatro archivos de salida**
        output_files = {}

        # 📌 1. Planificación de Pedidos
        output_files["Planificación de Pedidos"] = io.BytesIO()
        df.to_excel(output_files["Planificación de Pedidos"], index=False, engine='xlsxwriter')
        output_files["Planificación de Pedidos"].seek(0)

        # 📌 2. Errores en CajasCapas
        df_errores = df[df["cajascapas"] == 0][["pedido", "cajascapas", "cajaspalet"]]
        output_files["Errores en CajasCapas"] = io.BytesIO()
        df_errores.to_excel(output_files["Errores en CajasCapas"], index=False, engine='xlsxwriter')
        output_files["Errores en CajasCapas"].seek(0)

        # 📌 3. Productos para Descatalogar
        df_descatalogar = df[(df["21 días"] < 5) | (df["21 días"] == 0)]
        output_files["Productos para Descatalogar"] = io.BytesIO()
        df_descatalogar.to_excel(output_files["Productos para Descatalogar"], index=False, engine='xlsxwriter')
        output_files["Productos para Descatalogar"].seek(0)

        # 📌 4. Pedido para SAP
        df["Pallets Pedido (Original)"] = (df["pedido"] / df["cajaspalet"]).fillna(0).round(2)
        df["Pedido Completo SAP"] = df["pedido"]
        df_pedido_sap = df[df["pedido"] > 0][
            ["pedido", "Pallets Pedido (Original)", "cajaspalet", "Pallets Pedido", "Pedido Completo SAP"]
        ]
        output_files["Pedido para SAP"] = io.BytesIO()
        df_pedido_sap.to_excel(output_files["Pedido para SAP"], index=False, engine='xlsxwriter')
        output_files["Pedido para SAP"].seek(0)

        # 📥 Botones para descargar los archivos
        st.success("✅ ¡Archivos generados correctamente!")
        for nombre, archivo in output_files.items():
            st.download_button(
                label=f"📥 Descargar {nombre}",
                data=archivo,
                file_name=f"{nombre.replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
else:
    st.warning("📤 **Por favor, sube un archivo Excel para comenzar.**")
