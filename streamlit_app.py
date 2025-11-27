import streamlit as st
import pandas as pd
import io

from shotmarker_parser import parse_shotmarker_csv
from plot_target import plot_target_with_scores
from score_parser import parse_scores_csv
from app_utils import (
    create_shooter_report,
    get_match_number,
    _to_int_score,
    _display_score
)

# Must be the first Streamlit call in the file (move this right after `import streamlit as st`)
st.set_page_config(page_title="MRPC Shotmarker Data Explorer", layout="wide")

st.title("MRPC Shotmarker Data Explorer")
st.write(
    "Upload your MRPC shotmarker data files to visualize and analyze your shooting sessions."
)

# optional CSS to ensure the block container uses full width
st.markdown("<style>div.block-container{padding-left:1rem;padding-right:1rem;max-width:100%;}</style>", unsafe_allow_html=True)

uploaded_files = st.sidebar.file_uploader(
    "Choose MRPC shotmarker data files", accept_multiple_files=True, type=["csv", "xlsx"]
)

# Second upload button for scores CSV
scores_uploaded_file = st.sidebar.file_uploader(
    "Choose scores CSV file", accept_multiple_files=False, type=["csv"]
)

# Process scores CSV file if uploaded (display above shot strings)
df_scores = None
user_mapping = {}
if scores_uploaded_file:
    st.header("Scores Data")
    try:
        df_scores = parse_scores_csv(scores_uploaded_file)
        
        # Add relay, match, and target columns if they don't exist
        if 'relay' not in df_scores.columns:
            df_scores['relay'] = ''
        if 'match_id' not in df_scores.columns:
            df_scores['match_id'] = ''
        if 'target' not in df_scores.columns:
            df_scores['target'] = ''
        
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
    
    # ============================================================================
    # STEP 1: Create comprehensive mapping from shotmarker strings to metadata
    # ============================================================================
    # Build a single mapping dictionary with all metadata for each unique_id
    # This is more efficient than creating separate mappings and extracting from DataFrames
    shotmarker_metadata = {}
    for string in all_strings:
        unique_id = string.get('unique_id', '')
        if not unique_id:
            continue
        
        # Extract relay and match from DataFrame (all rows have same values)
        relay = None
        match_id = None
        if 'data' in string and string['data'] is not None:
            if 'relay' in string['data'].columns:
                relay_vals = string['data']['relay'].dropna().unique()
                relay = relay_vals[0] if len(relay_vals) > 0 else None
            if 'match' in string['data'].columns:
                match_vals = string['data']['match'].dropna().unique()
                match_id = match_vals[0] if len(match_vals) > 0 else None
        
        shotmarker_metadata[unique_id] = {
            'relay': relay,
            'match_id': match_id,
            'target': string.get('rifle', ''),
            'shooter': string.get('shooter', ''),
            'string_data': string  # Keep reference to full string for later merging
        }
    
    # ============================================================================
    # STEP 2: Enrich scores DataFrame with shotmarker metadata
    # ============================================================================
    if df_scores is not None and 'uniq_id' in df_scores.columns:
        # Ensure required columns exist
        for col in ['relay', 'match_id', 'target']:
            if col not in df_scores.columns:
                df_scores[col] = ''
        
        # Map shotmarker metadata to scores DataFrame in one pass
        def get_metadata_value(uniq_id, key):
            """Helper to safely get metadata value"""
            metadata = shotmarker_metadata.get(uniq_id, {})
            return metadata.get(key, '')
        
        # Apply mappings efficiently
        df_scores['relay'] = df_scores['uniq_id'].apply(lambda x: get_metadata_value(x, 'relay') or '')
        df_scores['match_id'] = df_scores['uniq_id'].apply(lambda x: get_metadata_value(x, 'match_id') or '')
        df_scores['target'] = df_scores['uniq_id'].apply(lambda x: get_metadata_value(x, 'target') or '')
        
        # Forward-fill missing values: match_id by match group, relay/target by user group
        # Use pandas ffill/bfill which is more efficient than custom lambda functions
        if 'match' in df_scores.columns and 'match_id' in df_scores.columns:
            # Replace empty strings with NaN for forward-fill
            df_scores['match_id'] = df_scores['match_id'].replace('', pd.NA)
            # Forward-fill within each match group
            df_scores['match_id'] = df_scores.groupby('match')['match_id'].ffill().bfill()
            df_scores['match_id'] = df_scores['match_id'].fillna('')
        
        if 'user' in df_scores.columns:
            for col in ['relay', 'target']:
                if col in df_scores.columns:
                    df_scores[col] = df_scores[col].replace('', pd.NA)
                    # Forward-fill within each user group
                    df_scores[col] = df_scores.groupby('user')[col].ffill().bfill()
                    df_scores[col] = df_scores[col].fillna('')
        
        # Display updated df_scores after population
        st.subheader("Updated Scores Data (After Merging)")
        st.write(f"Updated {len(df_scores)} rows with relay, match_id, and target data")
        st.dataframe(df_scores, use_container_width=True)
    
    # ============================================================================
    # STEP 3: Update shooter names and merge scores data into shotmarker strings
    # ============================================================================
    # Create a lookup dictionary from scores DataFrame for efficient access
    scores_lookup = {}
    user_col = None  # Initialize outside the if block
    
    if df_scores is not None and 'uniq_id' in df_scores.columns:
        # Standardize column name for user lookup
        for col_name in ['user', 'User', 'USER']:
            if col_name in df_scores.columns:
                user_col = col_name
                break
        
        # Create lookup: uniq_id -> row data (as dict for easy access)
        for _, row in df_scores.iterrows():
            uniq_id = row['uniq_id']
            if uniq_id:
                scores_lookup[uniq_id] = row.to_dict()
    
    # Update shotmarker strings with user data and merge scores
    for string in all_strings:
        unique_id = string.get('unique_id', '')
        if not unique_id or unique_id not in scores_lookup:
            continue
        
        scores_row = scores_lookup[unique_id]
        
        # Update shooter name from scores CSV
        user_from_scores = scores_row.get(user_col, '') if user_col else ''
        if user_from_scores:
            string['shooter'] = user_from_scores
            rifle_from_shotmarker = string.get('rifle', '')
            new_shooter_name = f"{user_from_scores} {rifle_from_shotmarker}".strip()
            
            # Update shooter_name in DataFrame
            if 'data' in string and string['data'] is not None and 'shooter_name' in string['data'].columns:
                string['data']['shooter_name'] = new_shooter_name
        
        # Merge scores data into shotmarker DataFrame
        if 'data' in string and string['data'] is not None:
            # Add unique_id to shotmarker DataFrame for reference
            df_shotmarker = string['data'].copy()
            df_shotmarker['unique_id'] = unique_id
            
            # Convert scores row to DataFrame and merge
            df_scores_row = pd.DataFrame([scores_row])
            # Rename uniq_id to unique_id for consistent merging
            if 'uniq_id' in df_scores_row.columns:
                df_scores_row = df_scores_row.rename(columns={'uniq_id': 'unique_id'})
            
            # Merge: use left join to keep all shotmarker rows, add scores columns
            df_combined = pd.merge(
                df_shotmarker, 
                df_scores_row, 
                on='unique_id', 
                how='left', 
                suffixes=('', '_scores')
            )
            string['data'] = df_combined
    
    # Display merged dataframes under scores section
    # if merged_dataframes and scores_uploaded_file:
    #     st.subheader("Merged Data (Shotmarker + Scores)")
    #     for merged_info in merged_dataframes:
    #         st.write(f"**Unique ID:** {merged_info['unique_id']} | **Shooter:** {merged_info['shooter']}")
    #         st.dataframe(merged_info['data'], use_container_width=True)
    #         st.divider()


    
    # Group strings by shooter name and sort by match
    
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
    
    # Add dropdown to select shooter in sidebar
    if len(sorted_shooters) > 0:
        # Add "All Shooters" option at the beginning
        shooter_options = ["All Shooters"] + sorted_shooters
        selected_shooter = st.sidebar.selectbox(
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
            if strings:
                first_string = strings[0]
                # Get relay from df_scores if available
                relay_value = ''
                if df_scores is not None and 'uniq_id' in df_scores.columns and 'relay' in df_scores.columns:
                    unique_id = first_string.get('unique_id', '')
                    if unique_id:
                        matching_rows = df_scores[df_scores['uniq_id'] == unique_id]
                        if not matching_rows.empty:
                            relay_value = matching_rows.iloc[0]['relay']
                            if pd.isna(relay_value) or relay_value == '':
                                relay_value = ''
                            else:
                                relay_value = f" | Relay: {relay_value}"
                
                st.subheader(f"Date: {first_string['date']} | Target: {first_string['rifle']}{relay_value}")
                
            # Create shooter report and download button
            # report_buf = create_shooter_report(shooter, strings, get_match_number)
            # if report_buf:
            #     st.download_button(
            #         label=f"📥 Download {shooter} Report (PNG)",
            #         data=report_buf,
            #         file_name=f"shooter_report_{shooter.replace(' ', '_')}.png",
            #         mime="image/png",
            #         key=f"download_report_{shooter}"
            #     )
            #     report_buf.close()
            
            st.divider()
            
            # Display all strings for this shooter inside the container
            for i, string in enumerate(strings):
                # Get match number for display
                match_num = get_match_number(string)
                match_display = f"Match {match_num}" if match_num != 999 else "Match Unknown"
                
                # Get match value from df_scores if available
                match_value = ''
                if df_scores is not None and 'uniq_id' in df_scores.columns and 'match' in df_scores.columns:
                    unique_id = string.get('unique_id', '')
                    if unique_id:
                        matching_rows = df_scores[df_scores['uniq_id'] == unique_id]
                        if not matching_rows.empty:
                            match_val = matching_rows.iloc[0]['match']
                            if not pd.isna(match_val) and match_val != '':
                                match_value = f"Match: {match_val}, "
                
                #st.subheader(f"{match_display} - {string['stage']}")
                st.write(f"{match_value}Target Type: {string['course']}, Score: {string['score']}")
                
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
                numeric_scores = df['score'].apply(_to_int_score)

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
                # buf = io.BytesIO()
                # fig.savefig(buf, format='png')
                # buf.seek(0)
                # st.download_button(
                #     label="Download Target Plot as PNG",
                #     data=buf,
                #     file_name=f"target_plot_{shooter}_match_{match_num}_string_{i+1}.png",
                #     mime="image/png"
                # )
                # buf.close()
            
            # Add spacing between shooter containers
            st.markdown("<br>", unsafe_allow_html=True)
            