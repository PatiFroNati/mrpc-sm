import streamlit as st

st.title("MRPC Shotmarker Data Explorer")
st.write(
    "Upload your MRPC shotmarker data files to visualize and analyze your shooting sessions."
)
uploaded_files = st.file_uploader(
    "Choose MRPC shotmarker data files", accept_multiple_files=True, type=["csv"]
)   

