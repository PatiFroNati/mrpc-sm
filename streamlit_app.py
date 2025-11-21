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

st.title("MRPC Shotmarker Data Explorer")
st.write(
    "Upload your MRPC shotmarker data files to visualize and analyze your shooting sessions."
)
uploaded_files = st.file_uploader(
    "Choose MRPC shotmarker data files", accept_multiple_files=True, type=["csv"]
)   

def parse_shotmarker_csv(filepath):
    """Parse the ShotMarker CSV file with multiple shooting strings."""
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    all_strings = []
    current_string = None
    current_data = []
    
    for line in lines:
        line = line.strip()
        
        if not line or line.startswith('ShotMarker') or line.startswith('Exported'):
            continue
            
        # Check if this is a new string header
        if line.startswith('Nov ') and ',' in line:
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 6:
                # Save previous string
                if current_string and current_data:
                    df = pd.DataFrame(current_data)
                    current_string['data'] = df
                    all_strings.append(current_string)
                
                # Parse shooter and stage from parts[1]
                shooter_stage = parts[1] if parts[1] else ''
                tokens = shooter_stage.split()
                shooter = tokens[0] if tokens else ''
                stage = ' '.join(tokens[1:]) if len(tokens) > 1 else ''
                
                # Start new string
                current_string = {
                    'date': parts[0],
                    'shooter': shooter,
                    'stage': stage,
                    'rifle': parts[2],
                    'target_info': parts[3],
                    'course': parts[4],
                    'score': parts[5]
                }
                current_data = []
                continue
        
        if line.startswith(',time,'):
            continue
        
        if line.startswith(',') and current_string:
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 13:
                try:
                    shot_data = {
                        'time': parts[1],
                        'tags': parts[2],
                        'id': parts[3],
                        'score': parts[4],
                        'temp_c': float(parts[5]) if parts[5] else None,
                        'x_mm': float(parts[6]) if parts[6] else None,
                        'y_mm': float(parts[7]) if parts[7] else None,
                        'v_fps': float(parts[8]) if parts[8] else None,
                        'yaw_deg': float(parts[9]) if parts[9] else None,
                        'pitch_deg': float(parts[10]) if parts[10] else None,
                        'quality': float(parts[11]) if parts[11] else None,
                        'xy_err': float(parts[12]) if parts[12] else None
                    }
                    current_data.append(shot_data)
                except (ValueError, IndexError):
                    continue
    
    # Add final string
    if current_string and current_data:
        df = pd.DataFrame(current_data)
        current_string['data'] = df
        all_strings.append(current_string)
    
    return all_strings

if uploaded_files:
    for uploaded_file in uploaded_files:
        st.header(f"File: {uploaded_file.name}")
        strings = parse_shotmarker_csv(uploaded_file)
        
        for i, string in enumerate(strings):
            st.subheader(f"Shooting String {i+1}: {string['shooter']} - {string['stage']}")
            st.write(f"Date: {string['date']}, Rifle: {string['rifle']}, Course: {string['course']}, Score: {string['score']}")
            
            df = string['data']
            st.dataframe(df)
            
            



