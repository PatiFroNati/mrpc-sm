import pandas as pd
import streamlit as st

def parse_scores_csv(scores_uploaded_file):
    """
    Parse an uploaded CSV file into a pandas DataFrame.
    Strips out any rows before the row that starts with 'Match'.
    Adds a uniq_id column where total comes first, then shots.
    
    Parameters:
        scores_uploaded_file: Streamlit uploaded file object (st.file_uploader)
    
    Returns:
        pd.DataFrame with an added uniq_id column
    """
    # Read the raw file into a DataFrame
    df = pd.read_csv(scores_uploaded_file)
    
    # Find the first row where 'match' equals 'Match'
    if "Match" in df.columns:
        # Already parsed correctly, no need to strip
        pass
    else:
        # If the file has extra rows before headers, reload with skiprows
        uploaded_file.seek(0)  # reset file pointer
        # Read all lines
        lines = uploaded_file.readlines()
        # Find index of line starting with "match"
        start_idx = next(i for i, line in enumerate(lines) if line.decode().startswith("Match"))
        # Reload DataFrame from that line onward
        uploaded_file.seek(0)
        df_scores = pd.read_csv(pd.compat.StringIO("".join([l.decode() for l in lines[start_idx:]])))
    
    # Create uniq_id with total first, then shots
    df_scores["uniq_id"] = df_scores["total"].astype(str) + "," + df_scores ["shots"].astype(str)
    
    return df_scores

