import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import io
import re
from PIL import Image

from plot_target import plot_target_with_scores


def get_match_number(string):
    """
    Extract match number from a string dict for sorting purposes.
    Returns the match number as an int, or 999 if not found.
    """
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


def _to_int_score(s):
    """
    Convert a score value to an integer for calculations.
    Treats 'x' or 'X' as 10, handles NaN and other edge cases.
    """
    if pd.isna(s):
        return 0
    if isinstance(s, str) and s.strip().lower() == 'x':
        return 10
    try:
        return int(float(s))
    except Exception:
        return 0


def _display_score(s):
    """
    Convert a score value to a display string.
    Preserves 'X' for x values, converts numbers to strings.
    """
    if pd.isna(s):
        return ''
    if isinstance(s, str) and s.strip().lower() == 'x':
        return 'X'
    try:
        return str(int(float(s)))
    except Exception:
        return str(s)


def create_shooter_report(shooter_name, strings, get_match_number_func):
    """
    Create a combined PNG report for a shooter with all their matches.
    Returns a BytesIO buffer containing the PNG image.
    
    Args:
        shooter_name: Name of the shooter
        strings: List of string dicts for this shooter
        get_match_number_func: Function to extract match number from a string dict
    
    Returns:
        BytesIO buffer containing the PNG image, or None if no strings
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
        match_num = get_match_number_func(string)
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

