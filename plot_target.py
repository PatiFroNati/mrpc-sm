import matplotlib.pyplot as plt
from matplotlib.patches import Circle



def plot_target_with_scores(string_data, target_size_mm=None):
    """Enhanced target plot with shot scores and calculated target size."""
    
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    
    df = string_data['data']
    sighters = df[df['tags'] == 'sighter']
    shots = df[df['tags'] != 'sighter']
    
    # Calculate target size based on farthest shots
    if target_size_mm is None:
        x_max = shots['x_mm'].abs().max() if len(shots) > 0 else 0
        y_max = shots['y_mm'].abs().max() if len(shots) > 0 else 0
        farthest = max(x_max, y_max)
        target_size_mm = (farthest * 2 + 25) // 50 * 50  # Round up to nearest 50mm and add 25mm
        if target_size_mm < 50:
            target_size_mm = 50
    
    # Draw target rings
    for radius_fraction in [1.0, 0.8, 0.6, 0.4, 0.2]:
        radius = target_size_mm/2 * radius_fraction
        circle = Circle((0, 0), radius, fill=False, 
                       edgecolor='black', linewidth=1.5, alpha=0.8)
        ax.add_patch(circle)
    
    # X-ring
    x_ring = Circle((0, 0), target_size_mm/2 * 0.1, fill=False,
                   edgecolor='red', linewidth=2.5)
    ax.add_patch(x_ring)
    
    # Plot shots with IDs inside markers
    if len(shots) > 0:
        ax.scatter(shots['x_mm'], shots['y_mm'], 
                  c='blue', s=150, alpha=0.6, 
                  edgecolors='darkblue', linewidth=2, label='Shots', zorder=5)
        
        for _, shot in shots.iterrows():
            ax.annotate(str(shot['id']), (shot['x_mm'], shot['y_mm']),
                       fontsize=8, ha='center', va='center',
                       color='white', weight='bold', zorder=6)
    
    # Plot sighters
    if len(sighters) > 0:
        ax.scatter(sighters['x_mm'], sighters['y_mm'],
                  c='orange', s=150, alpha=0.6,
                  edgecolors='darkorange', linewidth=2,
                  marker='s', label='Sighters', zorder=5)
        
        for _, shot in sighters.iterrows():
            label = f"{shot['id']}\n({shot['score']})"
            ax.annotate(label, (shot['x_mm'], shot['y_mm']),
                       fontsize=8, ha='center', va='center',
                       color='white', weight='bold')
    
    ax.set_aspect('equal')
    limit = target_size_mm / 2 * 1.1
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    ax.axvline(x=0, color='k', linestyle='--', alpha=0.3)
    ax.set_xlabel('Horizontal (mm)')
    ax.set_ylabel('Vertical (mm)')
    
    title = f"{string_data['shooter']} - {string_data['course']}\n{string_data['rifle']}\nScore: {string_data['score']}\nTarget: {target_size_mm}mm"
    ax.set_title(title, fontsize=11, weight='bold')
    ax.legend()
    
    return fig, ax