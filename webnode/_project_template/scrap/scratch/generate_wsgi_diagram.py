# scratch/generate_wsgi_diagram.py
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def generate_wsgi_diagram():
    # Set up figure size and dpi
    fig, ax = plt.subplots(figsize=(8, 10), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    
    # Hide grid and axes
    ax.axis('off')
    
    # Theme colors
    primary_color = '#1F497D'  # Corporate Dark Blue
    accent_color = '#2E75B6'   # Medium Blue
    bg_light = '#F2F4F7'       # Very Light Grey/Blue
    text_color = '#333333'
    white = '#FFFFFF'
    border_grey = '#D3D3D3'
    
    # Title
    ax.text(5, 11.5, "WSGI ADAPTER PIPELINE EXECUTION FLOW", 
            ha='center', va='center', fontsize=14, fontweight='bold', color=primary_color)
    
    # Helper for drawing process boxes
    def draw_box(y_center, title, lines):
        # Draw shadow
        shadow = patches.FancyBboxPatch(
            (1.55, y_center - 1.25), 6.9, 2.4, 
            boxstyle="round,pad=0.1", fc='#E6E6E6', ec='none', zorder=1
        )
        ax.add_patch(shadow)
        
        # Main box
        box = patches.FancyBboxPatch(
            (1.5, y_center - 1.2), 6.9, 2.4, 
            boxstyle="round,pad=0.1", fc=white, ec=primary_color, lw=2, zorder=2
        )
        ax.add_patch(box)
        
        # Header area shading
        header_bg = patches.FancyBboxPatch(
            (1.5, y_center + 0.6), 6.9, 0.6, 
            boxstyle="round,pad=0.1", fc=bg_light, ec='none', zorder=3
        )
        ax.add_patch(header_bg)
        
        # Header text
        ax.text(5, y_center + 0.9, title, 
                ha='center', va='center', fontsize=11, fontweight='bold', color=primary_color, zorder=4)
        
        # Line separating header
        ax.plot([1.5, 8.4], [y_center + 0.6, y_center + 0.6], color=primary_color, lw=1.5, zorder=4)
        
        # Body text
        y_text = y_center + 0.2
        for line in lines:
            ax.text(2.0, y_text, line, ha='left', va='center', fontsize=9.5, color=text_color, zorder=4)
            y_text -= 0.4
            
    # Helper for drawing input/output labels
    def draw_io_label(x, y, text, is_endpoint=False):
        fc = bg_light if not is_endpoint else primary_color
        txt_color = text_color if not is_endpoint else white
        font_wt = 'bold' if is_endpoint else 'normal'
        box = patches.FancyBboxPatch(
            (x - 2.0, y - 0.3), 4.0, 0.6, 
            boxstyle="round,pad=0.08", fc=fc, ec=primary_color, lw=1, zorder=2
        )
        ax.add_patch(box)
        ax.text(x, y, text, ha='center', va='center', fontsize=9, fontweight=font_wt, color=txt_color, zorder=3)
        
    # Helper for drawing connection arrows
    def draw_arrow(y_start, y_end, label_text=None):
        ax.annotate(
            '', xy=(5, y_end), xytext=(5, y_start),
            arrowprops=dict(arrowstyle="-|>", color=accent_color, lw=2.5, mutation_scale=15),
            zorder=2
        )
        if label_text:
            ax.text(5.2, (y_start + y_end)/2.0, label_text, 
                    ha='left', va='center', fontsize=8.5, color=accent_color, fontweight='bold', zorder=3)

    # 1. Starting Input: WSGI Web Server Host
    draw_io_label(5, 10.7, "[WSGI Web Server Host]", is_endpoint=True)
    draw_arrow(10.3, 9.5, "(environ, start_response)")
    
    # 2. Box 1: WSGIRequestWrapper
    draw_box(8.1, "wsgi.py (WSGIRequestWrapper)", [
        "• Parses standard WSGI variables (PATH_INFO, QUERY_STRING)",
        "• Decodes body stream from wsgi.input dynamically",
        "• Packages headers dictionary and client address context"
    ])
    draw_arrow(6.7, 5.7, "(Normalized RequestWrapper)")
    
    # 3. Box 2: ServerNode Flow
    draw_box(4.3, "ServerNode (start_flow)", [
        "• Walks the serialized Directed Acyclic Graph (DAG) sequentially",
        "• Executes security controls, routers, logic, and view nodes",
        "• Handles errors via dynamic stack trace validation maps"
    ])
    draw_arrow(2.9, 1.9, "(Response Object)")
    
    # 4. Box 3: create_app Interceptor
    draw_box(0.5, "wsgi.py (create_app Interceptor)", [
        "• Extracts response header list and HTTP status codes",
        "• Encodes body output string directly into raw data bytes",
        "• Automatically falls back to serve static directory resources"
    ])
    draw_arrow(-0.9, -2.1, "(Status Code + Header List + Bytes)")
    
    # 5. Ending Output: WSGI Server Response Outflow
    draw_io_label(5, -2.5, "[WSGI Server Response Outflow]", is_endpoint=True)
    
    # Adjust y-limits dynamically to crop the layout
    ax.set_ylim(-3.0, 12.0)
    
    plt.tight_layout()
    output_path = os.path.join(r"c:\Users\lifel\Downloads\framework\scratch", "wsgi_flow_diagram.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print("SUCCESS: Generated wsgi_flow_diagram.png in scratch/")

if __name__ == "__main__":
    generate_wsgi_diagram()
