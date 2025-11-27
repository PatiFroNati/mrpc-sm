# shotmarker_parser.py
import re
import pandas as pd
from typing import List, Dict, Any, Union

def parse_shotmarker_csv(uploaded_file: Union[bytes, str, "UploadedFile"]) -> List[Dict[str, Any]]:
    """
    Parse the ShotMarker CSV file with multiple shooting strings.
    Accepts bytes, str, or a file-like object with .getvalue().
    Returns a list of dicts; each dict has metadata and a pandas DataFrame under 'data'.
    """
    # get text content
    if hasattr(uploaded_file, "getvalue"):
        content = uploaded_file.getvalue()
        if isinstance(content, (bytes, bytearray)):
            text = content.decode("utf-8", errors="replace")
        else:
            text = str(content)
    elif isinstance(uploaded_file, (bytes, bytearray)):
        text = uploaded_file.decode("utf-8", errors="replace")
    elif isinstance(uploaded_file, str):
        text = uploaded_file
    else:
        raise TypeError("Unsupported uploaded_file type")

    lines = text.splitlines()

    all_strings = []
    current_string = None
    current_data = []

    header_re = re.compile(r'^[A-Z][a-z]{2}\b.*,\s*')  # month abbrev at line start followed by comma somewhere

    for line in lines:
        line = line.strip()
        if not line or line.startswith("ShotMarker") or line.startswith("Exported"):
            continue

        # Check if this is a new string header
        if header_re.match(line) and "," in line:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 6:
                # save previous
                if current_string and current_data:
                    current_string["data"] = pd.DataFrame(current_data)
                    # Add relay, match, and shooter_name columns
                    shooter_text = current_string.get("shooter", "")
                    rifle_text = current_string.get("rifle", "")
                    
                    # Extract relay (R followed by number, case-insensitive, anywhere in string)
                    relay_match = re.search(r'(?i)r(\d+)', shooter_text)
                    relay = relay_match.group(1) if relay_match else None
                    
                    # Extract match (M followed by number, case-insensitive, anywhere in string)
                    match_match = re.search(r'(?i)m(\d+)', shooter_text)
                    match = match_match.group(1) if match_match else None
                    
                    # Extract first word of shooter and concatenate with rifle
                    shooter_first_word = shooter_text.split()[0] if shooter_text.split() else ""
                    shooter_name = f"{shooter_first_word} {rifle_text}".strip() if shooter_first_word or rifle_text else ""
                    
                    # Add columns to dataframe
                    current_string["data"]["relay"] = relay
                    current_string["data"]["match"] = match
                    current_string["data"]["shooter_name"] = shooter_name
                    
                    # Create unique_id: total score + comma-separated individual shot scores
                    current_string["unique_id"] = current_string["score"] + "," + ",".join([str(shot["score"]) for shot in current_data])
                    all_strings.append(current_string)

                # parse shooter/stage
                shooter = ""
                stage = ""
                shooter_stage = parts[1] if parts[1] else ""
                tokens = shooter_stage.split()
                if tokens:
                    shooter = tokens[0]
                    stage = " ".join(tokens[1:]) if len(tokens) > 1 else ""

                # Extract rifle text between parentheses
                rifle_text = parts[2] if len(parts) > 2 else ""
                rifle_match = re.search(r'\(([^)]+)\)', rifle_text)
                rifle = rifle_match.group(1) if rifle_match else rifle_text
                
                current_string = {
                    "date": parts[0],
                    "shooter": shooter or "Unknown",
                    "stage": stage or "",
                    "rifle": rifle,
                    "target_info": parts[3] if len(parts) > 3 else "",
                    "course": parts[4] if len(parts) > 4 else "",
                    "score": parts[5] if len(parts) > 5 else "",
                }
                current_data = []
                continue

        # parse shot data lines when inside a string
        if current_string:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 13:
                x_str, y_str = parts[6], parts[7]
                if x_str and y_str:
                    try:
                        shot_data = {
                            "time": parts[1],
                            "tags": parts[2],
                            "id": parts[3],
                            "score": parts[4],
                            "temp_c": float(parts[5]) if parts[5] else None,
                            "x_mm": float(x_str),
                            "y_mm": float(y_str),
                            "v_fps": float(parts[8]) if parts[8] else None,
                            "yaw_deg": float(parts[9]) if parts[9] else None,
                            "pitch_deg": float(parts[10]) if parts[10] else None,
                            "quality": float(parts[11]) if parts[11] else None,
                            "xy_err": float(parts[12]) if parts[12] else None,
                            "target_info": current_string.get("course", ""),
                        }
                        current_data.append(shot_data)
                    except (ValueError, IndexError):
                        # skip malformed shot lines
                        continue

    # final string
    if current_string and current_data:
        current_string["data"] = pd.DataFrame(current_data)
        # Add relay, match, and shooter_name columns
        shooter_text = current_string.get("shooter", "")
        rifle_text = current_string.get("rifle", "")
        
        # Extract relay (R followed by number, case-insensitive, anywhere in string)
        relay_match = re.search(r'(?i)r(\d+)', shooter_text)
        relay = relay_match.group(1) if relay_match else None
        
        # Extract match (M followed by number, case-insensitive, anywhere in string)
        match_match = re.search(r'(?i)m(\d+)', shooter_text)
        match = match_match.group(1) if match_match else None
        
        # Extract first word of shooter and concatenate with rifle
        shooter_first_word = shooter_text.split()[0] if shooter_text.split() else ""
        shooter_name = f"{shooter_first_word} {rifle_text}".strip() if shooter_first_word or rifle_text else ""
        
        # Add columns to dataframe
        current_string["data"]["relay"] = relay
        current_string["data"]["match"] = match
        current_string["data"]["shooter_name"] = shooter_name
        
        # Create unique_id: total score + comma-separated individual shot scores
        current_string["unique_id"] = current_string["score"] + "," + ",".join([str(shot["score"]) for shot in current_data])
        # Calculate time between shots and add to DataFrame (if needed)
        # Convert time column to datetime if it's not already, then calculate diff
        current_string["data"]["time_between_shots"] = pd.to_datetime(current_string["data"]["time"], errors='coerce').diff().fillna(0)
        all_strings.append(current_string)

    return all_strings