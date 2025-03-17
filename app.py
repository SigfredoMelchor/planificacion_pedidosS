import pandas as pd
import io
from datetime import datetime

# Simulación de datos
data = {
    "articulo": ["A", "B", "C", "D", "E"],
    "descripción de artículo": ["Prod A", "Prod B", "Prod C", "Prod D", "Prod E"],
    "21 días": [100, 200, 300, 400, 500],
    "stock virtual": [50, 150, 250, 350, 450],
    "cajascapas": [10, 12, 15, 20, 25],
    "cajaspalet": [100, 120, 150, 200, 250],
    "pedido": [500, 360, 450, 660, 990],  # Simulación de pedidos base
}

df = pd.DataFrame(data)

# 📌 Calcular pallets pedido original
df["Pallets Pedido (Original)"] = (df["pedido"] / df["cajaspalet"]).fillna(0).round(2)

# 📌 Calcular el total de pallets
total_pallets = round(df["Pallets Pedido (Original)"].sum())

# 📌 Ajuste de Pedido Adicional para cumplir múltiplos de 33 pallets
falta_para_33 = (33 - (total_pallets % 33)) % 33
df["Pedido Adicional"] = 0
df["Pallets Pedido Adicional"] = 0

if falta_para_33 > 0:
    num_articulos_pedido_adicional = 3
    top_articulos = df.sort_values(by="21 días", ascending=False).head(num_articulos_pedido_adicional).index
    pedido_por_articulo = ((falta_para_33 / num_articulos_pedido_adicional) * df.loc[top_articulos, "cajaspalet"]).round().astype(int)
    pedido_por_articulo = (pedido_por_articulo // df.loc[top_articulos, "cajaspalet"]) * df.loc[top_articulos, "cajaspalet"]
    df.loc[top_articulos, "Pedido Adicional"] = pedido_por_articulo
    df["Pallets Pedido Adicional"] = (df["Pedido Adicional"] / df["cajaspalet"]).fillna(0).round(2)

df["Pallets Pedido Total"] = df["Pallets Pedido (Original)"] + df["Pallets Pedido Adicional"]
df["Pedido Completo SAP"] = df["pedido"] + df["Pedido Adicional"]

# 📌 Ajuste de pallets para optimizar el almacenamiento
def ajustar_pedido(row):
    pedido_original = row["Pedido Completo SAP"]
    ajuste = 0

    # Si el pedido está a menos de 1 capa del siguiente pallet, reducir al pallet completo
    if 0 < (pedido_original % row["cajaspalet"]) <= row["cajascapas"]:
        ajuste = - (pedido_original % row["cajaspalet"])
    # Si el pedido está a menos de 1 capa de completar el pallet, aumentarlo al pallet completo
    elif row["cajaspalet"] - (pedido_original % row["cajaspalet"]) <= row["cajascapas"]:
        ajuste = row["cajaspalet"] - (pedido_original % row["cajaspalet"])

    return ajuste

df["Ajuste Pedido"] = df.apply(ajustar_pedido, axis=1)
df["Pedido Final Ajustado"] = df["Pedido Completo SAP"] + df["Ajuste Pedido"]
df["Pallets Pedido Final"] = df["Pedido Final Ajustado"] / df["cajaspalet"]

# 📌 1. Planificación de Pedidos
df_planificacion = df.copy()

# 📌 2. Errores en CajasCapas
df_errores = df[df["cajascapas"] == 0][["pedido", "cajascapas", "cajaspalet"]]

# 📌 3. Productos para Descatalogar
df_descatalogar = df[(df["21 días"] < 5) | (df["21 días"] == 0)]

# 📌 4. Pedido para SAP (con ambos ajustes aplicados)
df_pedido_sap = df[(df["Pedido Final Ajustado"] > 0)][
    ["articulo", "descripción de artículo", "pedido", "Pallets Pedido (Original)", "Pedido Adicional",
     "Pallets Pedido Adicional", "cajaspalet", "Pallets Pedido Total", "Pedido Completo SAP",
     "Ajuste Pedido", "Pedido Final Ajustado", "Pallets Pedido Final"]
]

# 📌 Guardar archivos en memoria
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
output_files = {
    f"Planificacion_Pedidos_{timestamp}.xlsx": io.BytesIO(),
    f"Errores_CajasCapas_{timestamp}.xlsx": io.BytesIO(),
    f"Productos_Para_Descatalogar_{timestamp}.xlsx": io.BytesIO(),
    f"Pedido_para_SAP_{timestamp}.xlsx": io.BytesIO(),
}

df_planificacion.to_excel(output_files[f"Planificacion_Pedidos_{timestamp}.xlsx"], index=False, engine='xlsxwriter')
output_files[f"Planificacion_Pedidos_{timestamp}.xlsx"].seek(0)

df_errores.to_excel(output_files[f"Errores_CajasCapas_{timestamp}.xlsx"], index=False, engine='xlsxwriter')
output_files[f"Errores_CajasCapas_{timestamp}.xlsx"].seek(0)

df_descatalogar.to_excel(output_files[f"Productos_Para_Descatalogar_{timestamp}.xlsx"], index=False, engine='xlsxwriter')
output_files[f"Productos_Para_Descatalogar_{timestamp}.xlsx"].seek(0)

df_pedido_sap.to_excel(output_files[f"Pedido_para_SAP_{timestamp}.xlsx"], index=False, engine='xlsxwriter')
output_files[f"Pedido_para_SAP_{timestamp}.xlsx"].seek(0)

# 📌 Mostrar archivos para descargar
import ace_tools as tools
for filename, file in output_files.items():
    tools.display_dataframe_to_user(name=filename, dataframe=pd.read_excel(file))
