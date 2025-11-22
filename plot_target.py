import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.ticker import MultipleLocator

import json
import os

# Load target specs JSON from the project folder (same directory as this script)
TARGET_SPECS_RAW = {}
TARGET_SPECS = {}  # Dictionary indexed by type name for quick lookup
try:
    _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    _CANDIDATE_FILES = [
        os.path.join(_THIS_DIR, 'target_specs.json'),
        os.path.join(_THIS_DIR, 'target-specs.json'),
        os.path.join(_THIS_DIR, 'targets.json'),
    ]
    for _path in _CANDIDATE_FILES:
        if os.path.exists(_path):
            with open(_path, 'r', encoding='utf-8') as _f:
                TARGET_SPECS_RAW = json.load(_f)
            # Build a lookup dictionary by type name
            if 'targets' in TARGET_SPECS_RAW:
                for target in TARGET_SPECS_RAW['targets']:
                    TARGET_SPECS[target['type']] = target
            break
except Exception:
    TARGET_SPECS_RAW = {}
    TARGET_SPECS = {}
def get_target_spec_for(string_data):
    """Return target_spec dict: prefer string_data['target_spec'], else lookup by target type in TARGET_SPECS."""
    if isinstance(string_data, dict) and 'target_spec' in string_data:
        return string_data['target_spec']
    # Try to get target type from string_data and lookup in TARGET_SPECS
    target_type = None
    if isinstance(string_data, dict):
        # Try to get target type from shots if available
        data = string_data.get('data')
        if data is not None and hasattr(data, 'columns') and 'target_info' in data.columns:
            target_type = data['target_info'].iloc[0]
        elif 'target_type' in string_data:
            target_type = string_data['target_type']
    if target_type and target_type in TARGET_SPECS:
        return TARGET_SPECS[target_type]
    return None
    return TARGET_SPECS


def plot_target_with_scores(string_data, target_size_mm=None):
    """Enhanced target plot with shot scores and calculated target size."""
    
    fig, ax = plt.subplots(1, 1, figsize=(8,8))
    
    df = string_data['data']
    sighters = df[df['tags'] == 'sighter']
    shots = df[df['tags'] != 'sighter']
    
    # Calculate target size based on farthest shots
    if target_size_mm is None:
        x_max = shots['x_mm'].abs().max() if len(shots) > 0 else 0
        y_max = shots['y_mm'].abs().max() if len(shots) > 0 else 0
        farthest = max(x_max, y_max)
        import math
        target_size_mm = math.ceil((farthest * 2 + 25) / 50) * 50  # Round up to nearest 50mm and add 25mm
        if target_size_mm < 50:
            target_size_mm = 50
    
    ax.set_aspect('equal')
    limit = target_size_mm / 2 * 1.1
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    
    # Draw target rings based on specifications
    if len(shots) > 0 and 'target_info' in shots.columns:
        target_type = shots['target_info'].iloc[0]
        # Match target_type to spec by name
        spec = TARGET_SPECS.get(target_type)
        
        if spec:
            # Draw rings from largest to smallest (so smaller rings are on top)
            rings = spec.get('rings', [])
            # Sort by diameter descending to draw outer rings first
            rings_sorted = sorted(rings, key=lambda r: r.get('diameter', 0), reverse=True)
            
            for ring in rings_sorted:
                # Convert diameter to radius
                radius = ring.get('diameter', 0) / 2.0
                color = ring.get('color', '#000000')
                
                # Create circle with fill for better visibility
                circle = Circle((0, 0), radius, fill=True, 
                               facecolor=color, edgecolor='black',
                               linewidth=1, alpha=0.3, zorder=1)
                ax.add_patch(circle)
                
                # Add edge outline for clarity
                edge_circle = Circle((0, 0), radius, fill=False,
                                    edgecolor='black', linewidth=1.5, alpha=0.6, zorder=2)
                ax.add_patch(edge_circle)
    
    # Plot shots with IDs inside markers
    shot_handle = None
    sighter_handle = None
    if len(shots) > 0:
        shot_handle = ax.scatter(shots['x_mm'], shots['y_mm'], 
              c='blue', s=350, alpha=0.6, 
              edgecolors='darkblue', linewidth=2.5, label='Shots', zorder=5)
        
        for _, shot in shots.iterrows():
            ax.annotate(str(shot['id']), (shot['x_mm'], shot['y_mm']),
                   fontsize=8, ha='center', va='center',
                   color='white', weight='bold', zorder=6)
    # Plot sighters
    if len(sighters) > 0:
        sighter_handle = ax.scatter(sighters['x_mm'], sighters['y_mm'],
                  c='orange', s=150, alpha=0.6,
                  edgecolors='darkorange', linewidth=2,
                  marker='s', label='Sighters', zorder=5)
        
        for _, shot in sighters.iterrows():
            ax.annotate(str(shot['id']), (shot['x_mm'], shot['y_mm']),
                       fontsize=8, ha='center', va='center',
                       color='white', weight='bold', zorder=6)
    # Set grid size from target specs if available
    grid_size_mm = None
    if len(shots) > 0 and 'target_info' in shots.columns:
        target_type = shots['target_info'].iloc[0]
        spec = TARGET_SPECS.get(target_type)
        if spec and 'grid_size_moa_quarter' in spec:
            grid_size_mm = spec['grid_size_moa_quarter']
    
    if grid_size_mm:
        ax.xaxis.set_major_locator(MultipleLocator(grid_size_mm))
        ax.yaxis.set_major_locator(MultipleLocator(grid_size_mm))
    
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    limit = target_size_mm / 2 * 1.1
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    ax.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    ax.axvline(x=0, color='k', linestyle='--', alpha=0.3)
    # Removed x and y labels and hide tick labels (grid labels)
    ax.tick_params(axis='both', which='both', labelbottom=False, labelleft=False)
    title = f"{string_data['shooter']} - {string_data['course']}\n{string_data['rifle']}\nScore: {string_data['score']}\nTarget: {target_size_mm}mm"
    ax.set_title(title, fontsize=11, weight='bold')
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend()
    
    return fig, ax