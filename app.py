import streamlit as st
import tempfile
import shutil
import os
import subprocess
import pandas as pd

st.title("Zip File Processor")
st.write("Upload a `.zip` file and receive a processed `.csv` file in return.")

uploaded_files = st.file_uploader("Upload one or more .zip files", type="zip", accept_multiple_files=True)

if uploaded_files:
    tmpdir = tempfile.mkdtemp()
    
    # Guardar todos los zip en el mismo tmpdir
    for uploaded_file in uploaded_files:
        zip_path = os.path.join(tmpdir, uploaded_file.name)
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    
    st.success(f"Saved {len(uploaded_files)} zip files to temporary path: {tmpdir}")

    try:
        subprocess.run(["python3", "AutomaticASIS.py", tmpdir], check=True)
        subprocess.run(["python3", "InternalCalls.py", tmpdir], check=True)
    except subprocess.CalledProcessError:
        st.error("There was an error running the processing scripts.")
        st.stop()

    final_csv = os.path.join(tmpdir, "final_output.csv")

    if os.path.exists(final_csv):
        df = pd.read_csv(final_csv)
        st.write("Here's a preview of the final output CSV:")
        st.dataframe(df.head())

        with open(final_csv, "rb") as f:
            st.download_button(
                "Download final CSV",
                f,
                file_name="processed_result.csv",
                mime="text/csv"
            )
    else:
        st.error("Final CSV not found. Make sure your scripts write it to the temp directory.")