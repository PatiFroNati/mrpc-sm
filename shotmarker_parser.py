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
                    all_strings.append(current_string)

                # parse shooter/stage
                shooter = ""
                stage = ""
                shooter_stage = parts[1] if parts[1] else ""
                tokens = shooter_stage.split()
                if tokens:
                    shooter = tokens[0]
                    stage = " ".join(tokens[1:]) if len(tokens) > 1 else ""

                current_string = {
                    "date": parts[0],
                    "shooter": shooter or "Unknown",
                    "stage": stage or "",
                    "rifle": parts[2] if len(parts) > 2 else "",
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

                    #add a unique id that consists of the score from the current string concatenated with the scores from each shot
                    current_string["unique_id"] = current_string["score"] + ",".join([str(shot["score"]) for shot in current_data])

    # final string
    if current_string and current_data:
        current_string["data"] = pd.DataFrame(current_data)
        all_strings.append(current_string)

    return all_strings