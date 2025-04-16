# Crecimiento Infantil

Este proyecto es una aplicación interactiva desarrollada en Streamlit para el registro, seguimiento y visualización del crecimiento infantil, comparando los datos del niño/a con los estándares de la Organización Mundial de la Salud (OMS).

## Características principales
- Registro de datos de crecimiento: peso, estatura, perímetro cefálico, IMC, fecha de medición, etc.
- Cálculo automático de la edad en meses y del IMC.
- Visualización y edición dinámica de los datos ingresados.
- Comparación gráfica de los datos del niño/a con las curvas de referencia de la OMS (z-scores y percentiles) para diferentes indicadores:
  - Talla para la edad
  - Peso para la edad
  - Peso para la talla
  - IMC para la edad
  - Perímetro cefálico para la edad
- Descarga automática de los archivos de referencia OMS según sexo, edad e indicador.
- Guardado de los datos en archivos CSV.

## Requisitos
- Python 3.8+
- Las siguientes librerías (pueden instalarse con `pip install -r requirements.txt`):
  - streamlit
  - pandas
  - matplotlib
  - requests
  - urllib3
  - openpyxl

## Instalación y uso
1. Clona este repositorio y entra en la carpeta del proyecto.
2. (Opcional) Crea y activa un entorno virtual:
   ```
   python -m venv .venv
   # En Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   ```
3. Instala las dependencias:
   ```
   pip install -r requirements.txt
   ```
4. Ejecuta la aplicación:
   ```
   streamlit run TablaCrecimiento.py
   ```
5. Abre el navegador en la URL que indica Streamlit (por defecto http://localhost:8501).

## Estructura del proyecto
- `TablaCrecimiento.py`: Script principal de la aplicación Streamlit.
- `who_links.json`: Enlaces a los archivos de referencia de la OMS.
- `requirements.txt`: Dependencias del proyecto.
- `temp/`: Carpeta temporal para archivos descargados.
- Archivos CSV: Se generan al guardar los datos de cada niño/a.

## Notas
- Los datos de referencia se descargan automáticamente desde la OMS y se almacenan temporalmente.
- Los datos ingresados pueden exportarse a CSV para su respaldo o análisis posterior.

## Licencia
Este proyecto es de uso educativo y no sustituye el asesoramiento profesional médico.