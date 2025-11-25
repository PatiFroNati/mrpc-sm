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

# Must be the first Streamlit call in the file (move this right after `import streamlit as st`)
st.set_page_config(page_title="MRPC Shotmarker Data Explorer", layout="wide")

st.title("MRPC Shotmarker Data Explorer")
st.write(
    "Upload your MRPC shotmarker data files to visualize and analyze your shooting sessions."
)

# optional CSS to ensure the block container uses full width
st.markdown("<style>div.block-container{padding-left:1rem;padding-right:1rem;max-width:50%;}</style>", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Upload shot log data file", accept_multiple_files=False, type=["csv"])





if uploaded_files:
    for uploaded_file in uploaded_files:
        # st.header(f"File: {uploaded_file.name}")
        strings = parse_shotmarker_csv(uploaded_file)
        
        for i, string in enumerate(strings):
            st.subheader(f"Shooting String {i+1}: {string['shooter']} - {string['stage']}")
            st.write(f"Date: {string['date']}, Rifle: {string['rifle']}, Course: {string['course']}, Score: {string['score']}, Unique ID: {string['unique_id']}")
            
            df = string['data']
            summary_data = {
                "Shot Number": df['id'].values,
                "Score": df['score'].values,
                "Time": df['time'].values
            }
            summary_df = pd.DataFrame(summary_data)
            # transpose so rows become Shot Number, Score, Time and columns are each shot
            summary_df_t = summary_df.T
            # add a Total column (sums for each row)
            # convert scores for summing (treat 'x' or 'X' as 10) and prepare display values
            def _to_int_score(s):
                if pd.isna(s):
                    return 0
                if isinstance(s, str) and s.strip().lower() == 'x':
                    return 10
                try:
                    return int(float(s))
                except Exception:
                    return 0

            numeric_scores = df['score'].apply(_to_int_score)

            def _display_score(s):
                if pd.isna(s):
                    return ''
                if isinstance(s, str) and s.strip().lower() == 'x':
                    return 'X'
                try:
                    return str(int(float(s)))
                except Exception:
                    return str(s)

            # update Score row to display 'X' for x values
            if 'Score' in summary_df_t.index:
                summary_df_t.loc['Score'] = [_display_score(v) for v in df['score'].values]

            # add a Total column (sum of integer-converted scores, with blanks for non-score rows)
            # summary_df_t['Total'] = ['', int(numeric_scores.sum()), '']
            # st.dataframe(summary_df_t, use_container_width=True)
            # show plot and scores side-by-side
            left_col, right_col = st.columns([1, 4])
            result = plot_target_with_scores(string)
            fig = result[0] if isinstance(result, tuple) else result
            with left_col:
                st.pyplot(fig)
            with right_col:
                # display summary dataframe without a header and with row labels
                st.dataframe(summary_df_t, width='content', hide_index=False)

                # Show raw data toggle
                if st.checkbox(f"Show Raw Data for String {i+1}", key=f"raw_data_{i}"):
                    st.subheader(f"Raw Data for String {i+1}")
                    st.write(df)
            
            # do not close the figure here because it's used below for the download button
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

            
            


            



