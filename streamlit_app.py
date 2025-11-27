import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime
import os
import io
import re
from PIL import Image

from shotmarker_parser import parse_shotmarker_csv
from plot_target import plot_target_with_scores
from score_parser import parse_scores_csv

def create_shooter_report(shooter_name, strings, get_match_number):
    """
    Create a combined PNG report for a shooter with all their matches.
    Returns a BytesIO buffer containing the PNG image.
    """
    num_strings = len(strings)
    if num_strings == 0:
        return None
    
    # Calculate grid dimensions (prefer wider layout, max 3 columns)
    cols = min(3, num_strings)
    rows = (num_strings + cols - 1) // cols
    
    # Create figure with subplots
    fig = plt.figure(figsize=(cols * 5, rows * 5))
    fig.suptitle(f"Shooter Report: {shooter_name}", fontsize=16, weight='bold', y=0.995)
    
    # Store individual plot images as numpy arrays
    plot_images = []
    
    for string in strings:
        # Create individual plot
        result = plot_target_with_scores(string)
        plot_fig = result[0] if isinstance(result, tuple) else result
        
        # Convert plot to image and convert to numpy array before closing buffer
        plot_buf = io.BytesIO()
        plot_fig.savefig(plot_buf, format='png', dpi=100, bbox_inches='tight', pad_inches=0.2)
        plot_buf.seek(0)
        plot_img = Image.open(plot_buf)
        # Convert to numpy array so it doesn't depend on the buffer
        plot_img_array = np.array(plot_img)
        plot_images.append(plot_img_array)
        
        plt.close(plot_fig)  # Close the individual plot to free memory
        plot_buf.close()
    
    # Arrange images in grid
    for idx, (string, plot_img) in enumerate(zip(strings, plot_images)):
        ax = fig.add_subplot(rows, cols, idx + 1)
        
        # Display image in subplot
        ax.imshow(plot_img)
        ax.axis('off')
        
        # Add match info as title
        match_num = get_match_number(string)
        match_display = f"Match {match_num}" if match_num != 999 else "Match Unknown"
        ax.set_title(f"{match_display} - {string['stage']}\nScore: {string['score']}", 
                    fontsize=9, pad=5)
    
    plt.tight_layout(rect=[0, 0, 1, 0.98])  # Leave space for main title
    
    # Save to buffer
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    
    return buf

# Must be the first Streamlit call in the file (move this right after `import streamlit as st`)
st.set_page_config(page_title="MRPC Shotmarker Data Explorer", layout="wide")

st.title("MRPC Shotmarker Data Explorer")
st.write(
    "Upload your MRPC shotmarker data files to visualize and analyze your shooting sessions."
)

# optional CSS to ensure the block container uses full width
st.markdown("<style>div.block-container{padding-left:1rem;padding-right:1rem;max-width:100%;}</style>", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Choose MRPC shotmarker data files", accept_multiple_files=True, type=["csv", "xlsx"]
)

# Second upload button for scores CSV
scores_uploaded_file = st.file_uploader(
    "Choose scores CSV file", accept_multiple_files=False, type=["csv"]
)

# Process scores CSV file if uploaded (display above shot strings)
df_scores = None
user_mapping = {}
if scores_uploaded_file:
    st.header("Scores Data")
    try:
        df_scores = parse_scores_csv(scores_uploaded_file)
        st.write(f"Loaded {len(df_scores)} rows from {scores_uploaded_file.name}")
        st.dataframe(df_scores, use_container_width=True)
        
        # Create mapping from uniq_id to user column
        # Try common column names for user
        user_col = None
        for col_name in ['user', 'User', 'USER']:
            if col_name in df_scores.columns:
                user_col = col_name
                break
        
        if user_col:
            user_mapping = dict(zip(df_scores['uniq_id'], df_scores[user_col]))
        else:
            st.warning("Could not find 'user' column in scores CSV. Available columns: " + ", ".join(df_scores.columns))
        
        # Optionally show raw data toggle
        if st.checkbox("Show Raw Data Info", key="scores_raw_data"):
            st.subheader("DataFrame Info")
            st.write(f"Shape: {df_scores.shape}")
            st.write(f"Columns: {list(df_scores.columns)}")
    except Exception as e:
        st.error(f"Error processing scores CSV file: {str(e)}")

if uploaded_files:
    # Collect all strings from all uploaded files
    all_strings = []
    for uploaded_file in uploaded_files:
        strings = parse_shotmarker_csv(uploaded_file)
        all_strings.extend(strings)
    
    # Update shooter names from scores CSV if available
    # If unique_id matches, replace shooter_name with user from scores CSV + rifle from shotmarker data
    if user_mapping:
        for string in all_strings:
            unique_id = string.get('unique_id', '')
            if unique_id in user_mapping:
                user_from_scores = user_mapping[unique_id]
                rifle_from_shotmarker = string.get('rifle', '')
                # Concatenate user from scores with rifle from shotmarker
                new_shooter_name = f"{user_from_scores} {rifle_from_shotmarker}".strip()
                
                # Update shooter field
                string['shooter'] = user_from_scores
                
                # Update shooter_name in the DataFrame if it exists
                if 'data' in string and 'shooter_name' in string['data'].columns:
                    string['data']['shooter_name'] = new_shooter_name
    
    # Group strings by shooter name and sort by match
    # Extract match number for sorting (convert to int if possible)
    def get_match_number(string):
        match_val = None
        if 'data' in string and 'match' in string['data'].columns:
            # Get the first match value from the DataFrame (all rows should have the same match)
            match_vals = string['data']['match'].dropna().unique()
            if len(match_vals) > 0:
                match_val = match_vals[0]
        
        if match_val is None:
            # Try to extract from shooter_stage
            shooter_stage = string.get('shooter_stage', '')
            match_match = re.search(r'[Mm](\d+)', shooter_stage)
            match_val = match_match.group(1) if match_match else None
        
        try:
            return int(match_val) if match_val else 999
        except (ValueError, TypeError):
            return 999
    
    # Group by shooter name
    strings_by_shooter = {}
    for string in all_strings:
        shooter = string.get('shooter', 'Unknown')
        if shooter not in strings_by_shooter:
            strings_by_shooter[shooter] = []
        strings_by_shooter[shooter].append(string)
    
    # Sort each shooter's strings by match number
    for shooter in strings_by_shooter:
        strings_by_shooter[shooter].sort(key=get_match_number)
    
    # Sort shooters alphabetically
    sorted_shooters = sorted(strings_by_shooter.keys())
    
    # Add dropdown to select shooter
    if len(sorted_shooters) > 0:
        # Add "All Shooters" option at the beginning
        shooter_options = ["All Shooters"] + sorted_shooters
        selected_shooter = st.selectbox(
            "Select Shooter:",
            options=shooter_options,
            index=0,
            key="shooter_selector"
        )
        
        # Filter shooters based on selection
        if selected_shooter == "All Shooters":
            shooters_to_display = sorted_shooters
        else:
            shooters_to_display = [selected_shooter]
    else:
        shooters_to_display = []
    
    # Display grouped by shooter
    for shooter in shooters_to_display:
        strings = strings_by_shooter[shooter]
        
        # Create container for each shooter
        with st.container():
            st.header(f"Shooter: {shooter}")
            
            # Create shooter report and download button
            report_buf = create_shooter_report(shooter, strings, get_match_number)
            if report_buf:
                st.download_button(
                    label=f"📥 Download {shooter} Report (PNG)",
                    data=report_buf,
                    file_name=f"shooter_report_{shooter.replace(' ', '_')}.png",
                    mime="image/png",
                    key=f"download_report_{shooter}"
                )
                report_buf.close()
            
            st.divider()
            
            # Display all strings for this shooter inside the container
            for i, string in enumerate(strings):
                # Get match number for display
                match_num = get_match_number(string)
                match_display = f"Match {match_num}" if match_num != 999 else "Match Unknown"
                st.subheader(f"{match_display} - {string['stage']}")
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
                    if st.checkbox(f"Show Raw Data for {match_display}", key=f"raw_data_{shooter}_{i}"):
                        st.subheader(f"Raw Data for {match_display}")
                        st.write(df)
                
                # do not close the figure here because it's used below for the download button
                # Optionally, provide download link for the plot
                buf = io.BytesIO()
                fig.savefig(buf, format='png')
                buf.seek(0)
                st.download_button(
                    label="Download Target Plot as PNG",
                    data=buf,
                    file_name=f"target_plot_{shooter}_match_{match_num}_string_{i+1}.png",
                    mime="image/png"
                )
                buf.close()
            
            # Add spacing between shooter containers
            st.markdown("<br>", unsafe_allow_html=True)
            