import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import requests
import os
from datetime import datetime
import urllib3
import openpyxl  # Para leer archivos Excel

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#######################################
# CONFIGURACIÓN DE LA PÁGINA
#######################################
st.set_page_config(page_title="Tablero de Crecimiento Infantil", layout="wide")
st.title("Tablero de Crecimiento Infantil")

#######################################
# CARGA DEL ARCHIVO JSON
#######################################
@st.cache_data(show_spinner=False)
def load_links(json_file: str):
    with open(json_file, "r") as f:
        return json.load(f)

links_data = load_links("who_links.json")

#######################################
# FUNCIONES AUXILIARES
#######################################
def map_gender_to_key(gender_label: str) -> str:
    """Convierte 'Niño' -> 'boys' y 'Niña' -> 'girls'."""
    if gender_label == "Niño":
        return "boys"
    elif gender_label == "Niña":
        return "girls"
    return "boys"

def get_age_range(age_months: int, indicator: str = None) -> str:
    """
    Ajusta la lógica de rangos de edad según el indicador.
    """
    if indicator == "weight-for-age":
        return "0-13-weeks" if age_months < 3 else "0-5"
    elif indicator == "length-height-for-age":
        if age_months < 3:
            return "0-13-weeks"
        elif age_months < 24:
            return "0-2"
        else:
            return "2-5"
    elif indicator == "weight-for-length-height":
        return "0-2" if age_months < 24 else "2-5"
    elif indicator == "body-mass-index-for-age":
        if age_months < 3:
            return "0-13-weeks"
        elif age_months < 24:
            return "0-2"
        else:
            return "2-5"
    elif indicator == "head-circumference-for-age":
        return "0-13" if age_months <= 13 else "0-5"
    else:
        if age_months <= 24:
            return "0-2"
        elif age_months <= 60:
            return "2-5"
        else:
            return "0-5"

def get_reference_link(indicator: str, score_type: str, gender: str, age_months: int) -> str:
    """Obtiene la URL del Excel según indicador, tipo (z/p), sexo y rango."""
    gender_key = map_gender_to_key(gender)
    age_range = get_age_range(age_months, indicator)
    try:
        return links_data[indicator][score_type][gender_key][age_range]
    except KeyError:
        st.error(
            f"No se encontró link para indicador='{indicator}', tipo='{score_type}', "
            f"sexo='{gender_key}', rango='{age_range}'."
        )
        return None

#######################################
# DESCARGA Y LECTURA DE EXCEL
#######################################
def download_excel(url: str) -> str:
    """
    Descarga el archivo Excel a una carpeta local 'temp' dentro del proyecto,
    para evitar que se borre al recargar la app.
    """
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
    except Exception as e:
        st.error(f"Error al descargar Excel: {e}")
        return None

    if not os.path.exists("temp"):
        os.makedirs("temp")

    filename = url.split("/")[-1].split("?")[0]
    local_path = os.path.join("temp", filename)

    with open(local_path, "wb") as f:
        f.write(response.content)

    return local_path

def read_oms_excel(xlsx_path: str, indicator: str, score_type: str) -> pd.DataFrame:
    """
    Lee el archivo Excel con pandas, renombra columnas según sea z-score o percentil.
    """
    if not os.path.exists(xlsx_path):
        st.error(f"El archivo Excel {xlsx_path} no existe.")
        return None

    df = pd.read_excel(xlsx_path, sheet_name=0)
    st.write("**Vista previa del Excel:**")
    st.write(df.head())
    st.write("**Columnas detectadas:**", df.columns.tolist())

    # Diccionarios de renombrado
    rename_map_z = {
        "Month": "Edad (meses)",
        "Height": "Estatura (cm)",
        "SD3neg": "ZScore_-3",
        "SD2neg": "ZScore_-2",
        "SD1neg": "ZScore_-1",
        "SD0":    "ZScore_0",
        "SD1":    "ZScore_+1",
        "SD2":    "ZScore_+2",
        "SD3":    "ZScore_+3"
    }
    rename_map_p = {
        "Month": "Edad (meses)",
        "Height": "Estatura (cm)",
        "P3": "P3",
        "P5": "P5",
        "P50": "P50",
        "P85": "P85",
        "P97": "P97"
    }

    if score_type == "z":
        rename_map = rename_map_z
    else:
        rename_map = rename_map_p

    df = df.rename(columns=rename_map)

    # Determinar la columna X (edad o estatura)
    if indicator == "weight-for-length-height":
        x_col = "Estatura (cm)"
    else:
        x_col = "Edad (meses)"

    if x_col in df.columns:
        df[x_col] = pd.to_numeric(df[x_col], errors="coerce")
        df = df.dropna(subset=[x_col])

    # Manejo de z-scores
    if score_type == "z":
        for col in ["ZScore_-3", "ZScore_-2", "ZScore_-1", "ZScore_0", "ZScore_+1", "ZScore_+2", "ZScore_+3"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "ZScore_0" in df.columns:
            df = df.dropna(subset=["ZScore_0"])
    else:
        # Manejo de percentiles
        for col in ["P3", "P5", "P50", "P85", "P97"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

    return df

def get_reference_data(indicator: str, score_type: str, age_months: int, gender: str):
    """Descarga el Excel, lo lee, y retorna un diccionario con las columnas."""
    url = get_reference_link(indicator, score_type, gender, age_months)
    if not url:
        return None
    xlsx_path = download_excel(url)
    if not xlsx_path:
        return None

    df = read_oms_excel(xlsx_path, indicator, score_type)
    if df is None:
        return None

    return df.to_dict(orient="list")

#######################################
# ENTRADA DE DATOS DEL/LA NIÑO/A
#######################################
child_name = st.text_input("Nombre del Niño/Niña", value="Oliver")
child_gender = st.radio("Sexo", options=["Niño", "Niña"])
child_birthdate = st.date_input("Fecha de Nacimiento", value=datetime(2022, 2, 13))
today = datetime.now()
child_age_months = (today.year - child_birthdate.year)*12 + (today.month - child_birthdate.month)
st.subheader(f"Edad del/la niño/a: {child_age_months} meses")

st.markdown("### Ingresar Datos de Crecimiento")

# Datos iniciales (puedes tener varias filas de mediciones)
default_data = {
    "Fecha": [datetime(2024, 12, 14), datetime(2025, 3, 14)],
    "Edad (meses)": [child_age_months - 2, child_age_months],  # se recalcula más abajo
    "Peso (kg)": [13.5, 14],
    "Estatura (cm)": [92, 94],
    "Perímetro Cefálico (cm)": [None, 50],
    "IMC": [None, None]
}

# Manejo de la tabla en session_state
if "child_data" not in st.session_state:
    st.session_state["child_data"] = pd.DataFrame(default_data)

df_child = st.session_state["child_data"].copy()

def calcular_imc(row):
    try:
        peso = float(row["Peso (kg)"])
        est = float(row["Estatura (cm)"])
        if peso > 0 and est > 0:
            return round(peso / ((est / 100) ** 2), 2)
    except:
        pass
    return None

def calcular_edad_meses(birthdate: datetime, measurement_date: datetime):
    """Devuelve la diferencia en meses (aproximada) entre measurement_date y birthdate."""
    if pd.isnull(measurement_date):
        return None
    months = (measurement_date.year - birthdate.year)*12 + (measurement_date.month - birthdate.month)
    # Ajuste por días
    if measurement_date.day < birthdate.day:
        months -= 1
    return months

# Recalcula "Edad (meses)" e "IMC" antes de mostrar la tabla
df_child["Fecha"] = pd.to_datetime(df_child["Fecha"], errors="coerce")
df_child["Edad (meses)"] = df_child["Fecha"].apply(lambda d: calcular_edad_meses(child_birthdate, d))
df_child["IMC"] = df_child.apply(calcular_imc, axis=1)

# Configuración de columnas en data_editor
column_config = {
    "Fecha": st.column_config.DateColumn(
        "Fecha",
        format="YYYY-MM-DD",  # Ajusta el formato
        required=True
    ),
    "Edad (meses)": st.column_config.Column(
        "Edad (meses)",
        disabled=True
    ),
    "IMC": st.column_config.Column(
        "IMC",
        disabled=True
    )
}

df_edited = st.data_editor(
    df_child,
    num_rows="dynamic",
    use_container_width=True,
    column_config=column_config,
    key="child_data_editor"
)

st.session_state["child_data"] = df_edited

csv_filename = f"{child_name.replace(' ', '_')}_growth_data.csv"
if st.button("Guardar Datos"):
    st.session_state["child_data"].to_csv(csv_filename, index=False)
    st.success(f"Datos guardados en {csv_filename}")

#######################################
# FUNCIÓN PARA GRAFICAR COMPARACIÓN
#######################################
def compare_and_plot(indicator: str, score_type: str, child_metric: str, ylabel: str,
                     child_color: str, child_x_col: str = None):
    df_ref = get_reference_data(indicator, score_type, child_age_months, child_gender)
    if not df_ref:
        st.error("No se pudo obtener la información de referencia (OMS).")
        return

    # Determina la columna X en la OMS
    if indicator == "weight-for-length-height":
        x_label = "Estatura (cm)"
    else:
        x_label = "Edad (meses)"

    if x_label not in df_ref:
        st.error(f"Los datos OMS no contienen la columna '{x_label}'. Revisa el Excel o el renombrado.")
        return

    x_ref = df_ref[x_label]

    fig, ax = plt.subplots(figsize=(8, 5))

    # Lógica de z-scores vs percentiles
    if score_type == "z":
        zscore_keys = {
            "ZScore_-3": "-3 SD",
            "ZScore_-2": "-2 SD",
            "ZScore_-1": "-1 SD",
            "ZScore_0":  "0 SD",
            "ZScore_+1": "+1 SD",
            "ZScore_+2": "+2 SD",
            "ZScore_+3": "+3 SD"
        }
        curve_colors = {
            "ZScore_0": "green",
            "ZScore_-1": "yellow",
            "ZScore_+1": "yellow",
            "ZScore_-2": "orange",
            "ZScore_+2": "orange",
            "ZScore_-3": "red",
            "ZScore_+3": "red"
        }
        for key, label in zscore_keys.items():
            if key in df_ref:
                ax.plot(x_ref, df_ref[key], linestyle="--",
                        color=curve_colors.get(key, "black"), label=label)
    else:
        # Percentiles
        p_keys = {
            "P3": "P3",
            "P5": "P5",
            "P50": "P50",
            "P85": "P85",
            "P97": "P97"
        }
        p_colors = {
            "P3":  "red",
            "P5":  "orange",
            "P50": "green",
            "P85": "orange",
            "P97": "red"
        }
        for key, label in p_keys.items():
            if key in df_ref:
                ax.plot(x_ref, df_ref[key], linestyle="--",
                        color=p_colors.get(key, "black"), label=label)

    df_final = st.session_state["child_data"]
    if not child_x_col:
        if indicator == "weight-for-length-height":
            child_x_col = "Estatura (cm)"
        else:
            child_x_col = "Edad (meses)"

    if child_x_col in df_final.columns and child_metric in df_final.columns:
        ax.plot(df_final[child_x_col], df_final[child_metric], "o-",
                color=child_color, label=child_name)
    else:
        st.warning(f"No se encontró la columna '{child_x_col}' o '{child_metric}' en los datos del/la niño/a.")

    ax.set_title(f"{indicator} ({score_type.upper()})")
    if indicator == "weight-for-length-height":
        ax.set_xlabel("Estatura (cm)")
    else:
        ax.set_xlabel("Edad (meses)")
    ax.set_ylabel(ylabel)
    ax.legend()
    st.pyplot(fig)

#######################################
# SELECCIÓN DE INDICADOR
#######################################
st.markdown("### Selección del Indicador para Comparación")
indicator_options = list(links_data.keys())
selected_indicator = st.selectbox("Indicador", indicator_options)
score_type = st.selectbox("Tipo", ["z", "p"])

if selected_indicator == "length-height-for-age":
    compare_and_plot(selected_indicator, score_type,
                     child_metric="Estatura (cm)",
                     ylabel="Estatura (cm)",
                     child_color="blue")
elif selected_indicator == "weight-for-age":
    compare_and_plot(selected_indicator, score_type,
                     child_metric="Peso (kg)",
                     ylabel="Peso (kg)",
                     child_color="blue")
elif selected_indicator == "weight-for-length-height":
    compare_and_plot(selected_indicator, score_type,
                     child_metric="Peso (kg)",
                     ylabel="Peso (kg)",
                     child_color="blue")
elif selected_indicator == "body-mass-index-for-age":
    compare_and_plot(selected_indicator, score_type,
                     child_metric="IMC",
                     ylabel="IMC (kg/m²)",
                     child_color="blue")
elif selected_indicator == "head-circumference-for-age":
    compare_and_plot(selected_indicator, score_type,
                     child_metric="Perímetro Cefálico (cm)",
                     ylabel="Perímetro Cefálico (cm)",
                     child_color="blue")
else:
    st.warning("Indicador no soportado en la comparación.")