import streamlit as st
import tempfile
import shutil
import os
import subprocess
import pandas as pd

st.title("🔍 SAP Integration Suite explorer")
st.write("Selecciona uno o más paquetes (como archivos `.zip`) y descarga el reporte resultante.")

uploaded_files = st.file_uploader("Upload one or more .zip files", type="zip", accept_multiple_files=True)

if uploaded_files:
    tmpdir = tempfile.mkdtemp()
    
    # Guardar todos los zip en el mismo tmpdir
    for uploaded_file in uploaded_files:
        zip_path = os.path.join(tmpdir, uploaded_file.name)
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    
    st.success(f"Analizando {len(uploaded_files)} archivos...")

    try:
        subprocess.run(["python3", "AutomaticASIS.py", tmpdir], check=True)
        subprocess.run(["python3", "InternalCalls.py", tmpdir], check=True)
    except subprocess.CalledProcessError:
        st.error("Algo ha ido mal analizando los paquetes :( ")
        st.stop()

    final_csv = os.path.join(tmpdir, "final_output.csv")

    if os.path.exists(final_csv):
        df = pd.read_csv(final_csv)
        st.write("Aquí tienes una vista previa del archivo generado:")
        st.dataframe(df.head())

        with open(final_csv, "rb") as f:
            st.download_button(
                "Descargar reporte completo",
                f,
                file_name="processed_result.csv",
                mime="text/csv"
            )
    else:

        st.error("No se ha generado ningún reporte. Por favor, selecciona archivos correspondientes a paquetes de SAP Integration Suite.")

