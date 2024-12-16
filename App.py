# -*- coding: utf-8 -*-
"""
Created on Mon Dec 16 09:41:53 2024

@author: stp12
"""
import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz

# Funciones de preprocesamiento y cálculo
def match_aproximado(valor, lista_valores, threshold=30):
    if "ESCALERA" in valor.lower():
        return process.extractOne(valor, lista_valores, scorer=fuzz.partial_ratio)
    if "TORRE" in valor.lower():
        return process.extractOne(valor, lista_valores, scorer=fuzz.partial_ratio)
    match = process.extractOne(valor, lista_valores, scorer=fuzz.token_sort_ratio)
    if match and match[1] >= threshold:
        return match[0]
    return None

def calcular_fecha(row):
    if row['FECHA INICIO'].month != row['FECHA FIN'].month:
        return pd.Timestamp(year=row['FECHA FIN'].year, month=row['FECHA FIN'].month, day=1)
    else:
        return row['FECHA INICIO']

# Interfaz de Streamlit
st.title("Comparador de Alquileres")

# Menú para cargar los archivos Excel
st.sidebar.header("Cargar archivos")
uploaded_file1 = st.sidebar.file_uploader("Sube el archivo ESCALERAS OCTUBRE.xlsx", type=["xlsx"])
uploaded_file2 = st.sidebar.file_uploader("Sube el archivo MTBO202410.xlsx", type=["xlsx"])

if uploaded_file1 and uploaded_file2:
    # Cargar los archivos Excel
    df1 = pd.read_excel(uploaded_file1, header=None, names=['BARCO', 'ESTRUCTURA', 'FECHA INICIO', 'FECHA FIN', 'CANTIDAD', 'PRECIO', 'IMPORTE', 'OBSERVACIONES'], parse_dates=['FECHA INICIO', 'FECHA FIN'], dayfirst=True)
    df2 = pd.read_excel(uploaded_file2, header=None, names=['BARCO', 'ESTRUCTURA', 'FECHA INICIO', 'SUMINISTRO EXTRA', 'FECHA FIN', 'PRECIO SUMINISTRO', 'PRECIO ALQUILER', 'TOTAL SUMINISTRO', 'TOTAL ALQUILER', 'TOTAL FACTURA', 'OBSERVACIONES'], parse_dates=['FECHA INICIO', 'FECHA FIN'], dayfirst=True, index_col=None)

    # Preprocesar los datos
    df2.loc[df2['FECHA FIN'].isna(), 'FECHA FIN'] = pd.to_datetime('2024-10-31')
    df1["BARCO"] = df1["BARCO"].str.lower()
    df2["BARCO"] = df2["BARCO"].str.lower()
    df1["ESTRUCTURA"] = df1["ESTRUCTURA"].str.replace("METROS MUNDITUBO", "", regex=True).str.strip()
    df1 = df1[~(df1['ESTRUCTURA'].str.contains("TECHNOCRAFT|AIR TEK", case=False, na=False) | df1['OBSERVACIONES'].str.contains("JJ COVERS", case=False, na=False))]
    df2['FECHA CALCULO'] = df2.apply(calcular_fecha, axis=1)

    # Emparejar barcos y estructuras
    df1["barco_emparejado"] = df1["BARCO"].apply(lambda x: match_aproximado(x, df2["BARCO"].tolist(), threshold=40))
    df1["estructura_emparejada"] = df1["ESTRUCTURA"].apply(lambda x: match_aproximado(x, df2["ESTRUCTURA"].tolist(), threshold=40))

    # Comparar y obtener diferencias
    resultados = []
    for _, row in df1.iterrows():
        barco1 = row["BARCO"]
        barco2 = row["barco_emparejado"]
        estructura1 = row["ESTRUCTURA"]
        estructura2 = row["estructura_emparejada"]
        if barco2 and estructura2:
            match_row = df2[(df2["BARCO"] == barco2) & (df2["ESTRUCTURA"] == estructura2)]
            if not match_row.empty:
                match_row = match_row.iloc[0]
                dias_df1 = (pd.to_datetime(row["FECHA FIN"]) - pd.to_datetime(row["FECHA INICIO"])).days
                dias_df2 = (pd.to_datetime(match_row["FECHA FIN"]) - pd.to_datetime(match_row["FECHA CALCULO"])).days
                diferencia_dias = abs(dias_df1 - dias_df2)
                resultados.append({
                    "barco_1": barco1,
                    "barco_2": barco2,
                    "estructura_1": estructura1,
                    "estructura_2": estructura2,
                    "dias_df1": dias_df1,
                    "dias_df2": dias_df2,
                    "diferencia_dias": diferencia_dias,
                })

    # Crear DataFrame de resultados
    df_resultados = pd.DataFrame(resultados)

    # Filtrar las diferencias mayores a 4 días
    diferencias_mayores_4 = df_resultados[df_resultados["diferencia_dias"] > 4]
    diferencias_alquiler = []
    for _, row in diferencias_mayores_4.iterrows():
        barco_1 = row["barco_1"]
        barco_2 = row["barco_2"]
        estructura_1 = row["estructura_1"]
        estructura_2 = row["estructura_2"]
        fila_df1 = df1[(df1["BARCO"] == barco_1) & (df1["ESTRUCTURA"] == estructura_1)]
        fila_df2 = df2[(df2["BARCO"] == barco_2) & (df2["ESTRUCTURA"] == estructura_2)]
        for _, fila1 in fila_df1.iterrows():
            for _, fila2 in fila_df2.iterrows():
                diferencias_alquiler.append({
                    "BARCO_1": fila1["BARCO"],
                    "ESTRUCTURA_1": fila1["ESTRUCTURA"],
                    "FECHA_INICIO_1": fila1["FECHA INICIO"],
                    "FECHA_FIN_1": fila1["FECHA FIN"],
                    "BARCO_2": fila2["BARCO"],
                    "ESTRUCTURA_2": fila2["ESTRUCTURA"],
                    "FECHA_INICIO_2": fila2["FECHA INICIO"],
                    "FECHA_FIN_2": fila2["FECHA FIN"],
                    "DIFERENCIA_DIAS": row["diferencia_dias"]
                })
    df_diferencias_alquiler = pd.DataFrame(diferencias_alquiler)

    # Mostrar los resultados
    st.header("Resultados")
    st.subheader("Diferencias Alquiler")
    st.dataframe(df_diferencias_alquiler)

    st.subheader("Archivo 1 (ESCALERAS OCTUBRE)")
    st.dataframe(df1)

    st.subheader("Archivo 2 (MTBO202410)")
    st.dataframe(df2)

    # Opción para descargar los resultados
    st.download_button(
        label="Descargar Diferencias Alquiler",
        data=df_diferencias_alquiler.to_excel(index=False),
        file_name="diferencias_alquiler.xlsx"
    )

