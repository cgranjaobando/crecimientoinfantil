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
# DICCIONARIOS DE INDICADORES
#######################################
# Mostramos en el tablero nombres en español, pero internamente usamos inglés.
indicator_map_es = {
    "Talla para la edad": "length-height-for-age",
    "Peso para la edad": "weight-for-age",
    "Peso para la talla": "weight-for-length-height",
    "IMC para la edad": "body-mass-index-for-age",
    "Perímetro cefálico para la edad": "head-circumference-for-age"
}

#######################################
# FUNCIONES AUXILIARES
#######################################
def map_gender_to_key(gender_label: str) -> str:
    """Convierte 'Niño' -> 'boys' y 'Niña' -> 'girls'."""
    return "boys" if gender_label == "Niño" else "girls"

def get_age_range(age_months: int, indicator: str = None) -> str:
    """Ajusta la lógica de rangos de edad según el indicador."""
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
        return "0-2" if age_months <= 24 else "2-5"

def get_reference_link(indicator: str, score_type: str, gender: str, age_months: int) -> str:
    """Obtiene la URL del Excel OMS según indicador, tipo (z/p), sexo y rango."""
    gender_key = map_gender_to_key(gender)
    age_range = get_age_range(age_months, indicator)
    try:
        return links_data[indicator][score_type][gender_key][age_range]
    except KeyError:
        st.error(f"No se encontró link para '{indicator}', tipo='{score_type}', sexo='{gender_key}', rango='{age_range}'.")
        return None

#######################################
# MOSTRAR VENTANA DEL EXCEL
#######################################
def get_reference_window(df: pd.DataFrame, x_col: str, user_value: float, window: int = 5) -> pd.DataFrame:
    """Devuelve una ventana de 'window' filas centrada en el valor más cercano a user_value."""
    df_sorted = df.sort_values(by=x_col).reset_index(drop=True)
    diffs = (df_sorted[x_col] - user_value).abs()
    closest_index = diffs.idxmin()
    half_window = window // 2
    start = max(0, closest_index - half_window)
    end = start + window
    if end > len(df_sorted):
        end = len(df_sorted)
        start = max(0, end - window)
    return df_sorted.iloc[start:end]

#######################################
# DESCARGA Y LECTURA DE EXCEL
#######################################
def download_excel(url: str) -> str:
    """Descarga el archivo Excel a la carpeta local 'temp/' en el mismo directorio del script."""
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
    except Exception as e:
        st.error(f"Error al descargar Excel: {e}")
        return None

    script_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(script_dir, "temp")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    filename = url.split("/")[-1].split("?")[0]
    local_path = os.path.join(temp_dir, filename)

    with open(local_path, "wb") as f:
        f.write(response.content)

    return local_path

def read_oms_excel_original(xlsx_path: str) -> pd.DataFrame:
    """
    Lee el Excel OMS **sin renombrar** para mostrar la ventana centrada con nombres originales.
    """
    if not os.path.exists(xlsx_path):
        return None
    df_original = pd.read_excel(xlsx_path, sheet_name=0)
    return df_original

def rename_for_chart(df: pd.DataFrame, indicator: str, score_type: str) -> pd.DataFrame:
    """
    Crea una copia y renombra columnas SOLO para la lógica interna de la gráfica.
    No afecta la vista previa con columnas originales.
    """
    df_chart = df.copy()

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
    rename_map = rename_map_z if score_type == "z" else rename_map_p
    df_chart = df_chart.rename(columns=rename_map)

    if indicator == "weight-for-length-height":
        x_col = "Estatura (cm)"
    else:
        x_col = "Edad (meses)"

    # Convertir a numérico
    if x_col in df_chart.columns:
        df_chart[x_col] = pd.to_numeric(df_chart[x_col], errors="coerce")
        df_chart.dropna(subset=[x_col], inplace=True)

    if score_type == "z":
        # Z-scores
        for col in ["ZScore_-3", "ZScore_-2", "ZScore_-1", "ZScore_0", "ZScore_+1", "ZScore_+2", "ZScore_+3"]:
            if col in df_chart.columns:
                df_chart[col] = pd.to_numeric(df_chart[col], errors="coerce")
        if "ZScore_0" in df_chart.columns:
            df_chart.dropna(subset=["ZScore_0"], inplace=True)
    else:
        # Percentiles
        for col in ["P3", "P5", "P50", "P85", "P97"]:
            if col in df_chart.columns:
                df_chart[col] = pd.to_numeric(df_chart[col], errors="coerce")

    return df_chart

def get_reference_data(indicator: str, score_type: str, age_months: int, gender: str) -> pd.DataFrame:
    """Retorna un DataFrame renombrado para la gráfica, tras mostrar la ventana con nombres originales."""
    url = get_reference_link(indicator, score_type, gender, age_months)
    if not url:
        return pd.DataFrame()

    xlsx_path = download_excel(url)
    if not xlsx_path:
        return pd.DataFrame()

    # 1) Leemos el DataFrame original sin renombrar
    df_original = read_oms_excel_original(xlsx_path)
    if df_original is None or df_original.empty:
        return pd.DataFrame()

    # 2) Determinamos la columna X y el valor del usuario
    if indicator == "weight-for-length-height":
        x_col = "Height"  # Nombre original
        if "Estatura (cm)" in st.session_state["child_data"].columns:
            user_val = st.session_state["child_data"]["Estatura (cm)"].iloc[-1]
        else:
            user_val = None
    else:
        x_col = "Month"  # Nombre original
        user_val = st.session_state.get("child_age_months", None)

    # 3) Mostramos una ventana centrada en el valor del usuario con nombres originales
    if x_col in df_original.columns and user_val is not None:
        window_df = get_reference_window(df_original, x_col, user_val, window=5)
        st.write("**Vista previa OMS (ventana centrada con nombres originales):**")
        st.write(window_df)

    # 4) Creamos un df renombrado SOLO para la gráfica
    df_chart = rename_for_chart(df_original, indicator, score_type)
    return df_chart

#######################################
# ENTRADA DE DATOS DEL/LA NIÑO/A
#######################################
child_name = st.text_input("Nombre del Niño/Niña", value="Ingrese nombre del nino/a")
child_gender = st.radio("Sexo", options=["Niño", "Niña"])
child_birthdate = st.date_input("Fecha de Nacimiento", value=datetime(2022, 2, 13))
today = datetime.now()
child_age_months = (today.year - child_birthdate.year)*12 + (today.month - child_birthdate.month)
st.subheader(f"Edad del/la niño/a: {child_age_months} meses")
st.session_state["child_age_months"] = child_age_months

st.markdown("### Ingresar Datos de Crecimiento")

default_data = {
    "Fecha": [datetime(2024, 12, 14), datetime(2025, 3, 14)],
    "Edad (meses)": [child_age_months - 2, child_age_months],
    "Peso (kg)": [13.5, 14],
    "Estatura (cm)": [92, 94],
    "Perímetro Cefálico (cm)": [None, 50],
    "IMC": [None, None]
}

if "child_data" not in st.session_state:
    st.session_state["child_data"] = pd.DataFrame(default_data)

df_child = st.session_state["child_data"].copy()

def calcular_imc(row):
    try:
        peso = float(row["Peso (kg)"])
        est = float(row["Estatura (cm)"])
        if peso > 0 and est > 0:
            return round(peso / ((est/100)**2), 2)
    except:
        pass
    return None

def calcular_edad_meses(birthdate: datetime, measurement_date: datetime):
    if pd.isnull(measurement_date):
        return None
    months = (measurement_date.year - birthdate.year)*12 + (measurement_date.month - birthdate.month)
    if measurement_date.day < birthdate.day:
        months -= 1
    return months

df_child["Fecha"] = pd.to_datetime(df_child["Fecha"], errors="coerce")
df_child["Edad (meses)"] = df_child["Fecha"].apply(lambda d: calcular_edad_meses(child_birthdate, d))
df_child["IMC"] = df_child.apply(calcular_imc, axis=1)

column_config = {
    "Fecha": st.column_config.DateColumn("Fecha", format="YYYY-MM-DD", required=True),
    "Edad (meses)": st.column_config.Column("Edad (meses)", disabled=True),
    "IMC": st.column_config.Column("IMC", disabled=True)
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
# INDICADORES EN ESPAÑOL
#######################################
indicator_map_es = {
    "Talla para la edad": "length-height-for-age",
    "Peso para la edad": "weight-for-age",
    "Peso para la talla": "weight-for-length-height",
    "IMC para la edad": "body-mass-index-for-age",
    "Perímetro cefálico para la edad": "head-circumference-for-age"
}

#######################################
# FUNCIÓN PARA GRAFICAR COMPARACIÓN
#######################################
def compare_and_plot(indicator_en: str, indicator_es: str, score_type: str, child_metric: str,
                     ylabel: str, child_color: str, child_x_col: str = None):
    # Mostrar el enlace de referencia OMS
    url_ref = get_reference_link(indicator_en, score_type, child_gender, child_age_months)
    if url_ref:
        st.markdown(f"**[Link a datos OMS]({url_ref})**")

    df_ref = get_reference_data(indicator_en, score_type, child_age_months, child_gender)
    if df_ref is None or df_ref.empty:
        st.error("No se pudo obtener la información de referencia (OMS).")
        return

    if indicator_en == "weight-for-length-height":
        x_label = "Estatura (cm)"
    else:
        x_label = "Edad (meses)"

    if x_label not in df_ref.columns:
        st.error(f"Los datos OMS no contienen la columna '{x_label}'.")
        return

    x_ref = df_ref[x_label]

    # Preparar la figura
    fig, ax = plt.subplots(figsize=(8, 5))

    # Título en español
    titulo = f"{indicator_es} ({score_type.upper()})"

    # Z-scores vs. percentiles
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
            if key in df_ref.columns:
                ax.plot(x_ref, df_ref[key], linestyle="--",
                        color=curve_colors.get(key, "black"), label=label)
    else:
        p_keys = {
            "P3": "P3",
            "P5": "P5",
            "P50": "P50",
            "P85": "P85",
            "P97": "P97"
        }
        p_colors = {
            "P3": "red",
            "P5": "orange",
            "P50": "green",
            "P85": "orange",
            "P97": "red"
        }
        for key, label in p_keys.items():
            if key in df_ref.columns:
                ax.plot(x_ref, df_ref[key], linestyle="--",
                        color=p_colors.get(key, "black"), label=label)

    # Línea de evolución del niño
    df_final = st.session_state["child_data"]
    if not child_x_col:
        child_x_col = "Estatura (cm)" if indicator_en == "weight-for-length-height" else "Edad (meses)"
    if child_x_col in df_final.columns and child_metric in df_final.columns:
        ax.plot(df_final[child_x_col], df_final[child_metric], "o-",
                color=child_color, label=child_name)
    else:
        st.warning(f"No se encontró la columna '{child_x_col}' o '{child_metric}' en los datos del/la niño/a.")

    ax.set_title(titulo)
    ax.set_xlabel("Estatura (cm)" if indicator_en == "weight-for-length-height" else "Edad (meses)")
    ax.set_ylabel(ylabel)
    ax.legend()
    st.pyplot(fig)

#######################################
# SELECCIÓN DE INDICADOR (ESPAÑOL)
#######################################
st.markdown("### Selección del Indicador para Comparación")
indicator_es_list = list(indicator_map_es.keys())
selected_indicator_es = st.selectbox("Indicador", indicator_es_list)
score_type = st.selectbox("Tipo", ["z", "p"])

# Obtenemos la clave en inglés
selected_indicator_en = indicator_map_es[selected_indicator_es]

# Graficar según el indicador
if selected_indicator_en == "length-height-for-age":
    compare_and_plot(selected_indicator_en, selected_indicator_es, score_type,
                     child_metric="Estatura (cm)", ylabel="Estatura (cm)",
                     child_color="blue")

elif selected_indicator_en == "weight-for-age":
    compare_and_plot(selected_indicator_en, selected_indicator_es, score_type,
                     child_metric="Peso (kg)", ylabel="Peso (kg)",
                     child_color="blue")

elif selected_indicator_en == "weight-for-length-height":
    compare_and_plot(selected_indicator_en, selected_indicator_es, score_type,
                     child_metric="Peso (kg)", ylabel="Peso (kg)",
                     child_color="blue")

elif selected_indicator_en == "body-mass-index-for-age":
    compare_and_plot(selected_indicator_en, selected_indicator_es, score_type,
                     child_metric="IMC", ylabel="IMC (kg/m²)",
                     child_color="blue")

elif selected_indicator_en == "head-circumference-for-age":
    compare_and_plot(selected_indicator_en, selected_indicator_es, score_type,
                     child_metric="Perímetro Cefálico (cm)", ylabel="Perímetro Cefálico (cm)",
                     child_color="blue")

else:
    st.warning("Indicador no soportado en la comparación.")