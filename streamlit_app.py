import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime
import os
import io
from PIL import Image

from shotmarker_parser import parse_shotmarker_csv
from plot_target import plot_target_with_scores

st.title("MRPC Shotmarker Data Explorer")
st.write(
    "Upload your MRPC shotmarker data files to visualize and analyze your shooting sessions."
)
uploaded_files = st.file_uploader(
    "Choose MRPC shotmarker data files", accept_multiple_files=True, type=["csv", "excel"]
)   




if uploaded_files:
    for uploaded_file in uploaded_files:
        st.header(f"File: {uploaded_file.name}")
        strings = parse_shotmarker_csv(uploaded_file)
        
        for i, string in enumerate(strings):
            st.subheader(f"Shooting String {i+1}: {string['shooter']} - {string['stage']}")
            st.write(f"Date: {string['date']}, Rifle: {string['rifle']}, Course: {string['course']}, Score: {string['score']}")
            
            df = string['data']
            st.dataframe(df)
            result = plot_target_with_scores(string)
            fig = result[0] if isinstance(result, tuple) else result
            st.pyplot(fig)
            plt.close(fig)
            # Optionally, provide download link for the plot
            buf = io.BytesIO()
            fig.savefig(buf, format='png')
            buf.seek(0)
            st.download_button(
                label="Download Target Plot as PNG",
                data=buf,
                file_name=f"target_plot_string_{i+1}.png",
                mime="image/png"
            )
            buf.close()
            
            


            



