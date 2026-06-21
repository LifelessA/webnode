# scratch/generate_workflow_diagram.py
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def generate_workflow_diagram():
    # Set up figure size and dpi (tall format for vertical flowchart)
    fig, ax = plt.subplots(figsize=(10, 13), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(-3.0, 13.0)
    
    # Hide grid and axes
    ax.axis('off')
    
    # Theme colors
    primary_color = '#1F497D'   # Corporate Dark Blue (borders/headers)
    accent_color = '#2E75B6'    # Medium Blue (arrows)
    bg_light = '#F2F4F7'        # Very Light grey/blue (process blocks)
    bg_decision = '#FFF2CC'     # Light yellow (decision diamonds)
    bg_start_end = '#E2EFDA'    # Light sage green (start/end capsules)
    bg_error = '#FCE4D6'        # Light soft red/orange (error blocks)
    text_color = '#333333'
    white = '#FFFFFF'
    shadow_color = '#E6E6E6'
    
    # Title
    ax.text(5, 12.6, "WEB NODE FRAMEWORK: REQUEST-RESPONSE EXECUTION FLOW", 
            ha='center', va='center', fontsize=12, fontweight='bold', color=primary_color)
    
    # Helper to draw process blocks (rectangles)
    def draw_process(x_center, y_center, w, h, text, fill_color=bg_light):
        x = x_center - w/2.0
        y = y_center - h/2.0
        
        # Draw shadow
        shadow = patches.FancyBboxPatch(
            (x + 0.04, y - 0.04), w, h, 
            boxstyle="round,pad=0.03", fc=shadow_color, ec='none', zorder=1
        )
        ax.add_patch(shadow)
        
        # Main Box
        box = patches.FancyBboxPatch(
            (x, y), w, h, 
            boxstyle="round,pad=0.03", fc=fill_color, ec=primary_color, lw=1.5, zorder=2
        )
        ax.add_patch(box)
        
        # Text
        ax.text(x_center, y_center, text, 
                ha='center', va='center', fontsize=8, color=text_color, zorder=3,
                linespacing=1.4)

    # Helper to draw capsules (rounded start/end)
    def draw_capsule(x_center, y_center, w, h, text, fill_color=bg_start_end):
        x = x_center - w/2.0
        y = y_center - h/2.0
        
        # Draw shadow
        shadow = patches.FancyBboxPatch(
            (x + 0.04, y - 0.04), w, h, 
            boxstyle="round,pad=0.15", fc=shadow_color, ec='none', zorder=1
        )
        ax.add_patch(shadow)
        
        # Main Box
        box = patches.FancyBboxPatch(
            (x, y), w, h, 
            boxstyle="round,pad=0.15", fc=fill_color, ec=primary_color, lw=1.5, zorder=2
        )
        ax.add_patch(box)
        
        # Text
        ax.text(x_center, y_center, text, 
                ha='center', va='center', fontsize=8.5, fontweight='bold', color=primary_color, zorder=3)

    # Helper to draw decision diamonds
    def draw_decision(x_center, y_center, w, h, text, fill_color=bg_decision):
        pts = [
            (x_center, y_center - h/2.0), # bottom
            (x_center + w/2.0, y_center), # right
            (x_center, y_center + h/2.0), # top
            (x_center - w/2.0, y_center)  # left
        ]
        
        # Shadow polygon
        shadow_pts = [(px + 0.04, py - 0.04) for px, py in pts]
        shadow = patches.Polygon(shadow_pts, closed=True, fc=shadow_color, ec='none', zorder=1)
        ax.add_patch(shadow)
        
        # Main Polygon
        poly = patches.Polygon(pts, closed=True, fc=fill_color, ec=primary_color, lw=1.5, zorder=2)
        ax.add_patch(poly)
        
        # Text
        ax.text(x_center, y_center, text, 
                ha='center', va='center', fontsize=8.5, fontweight='bold', color=primary_color, zorder=3)

    # Helper to draw connector lines with labels
    def draw_arrow(x_start, y_start, x_end, y_end, label_text=None, label_pos='side'):
        ax.annotate(
            '', xy=(x_end, y_end), xytext=(x_start, y_start),
            arrowprops=dict(arrowstyle="-|>", color=accent_color, lw=2, mutation_scale=12),
            zorder=2
        )
        if label_text:
            x_label = (x_start + x_end) / 2.0
            y_label = (y_start + y_end) / 2.0
            if label_pos == 'side_yes':
                ax.text(x_label + 0.15, y_label, label_text, ha='left', va='center', fontsize=8, color=accent_color, fontweight='bold')
            elif label_pos == 'top_no':
                ax.text(x_label, y_label + 0.1, label_text, ha='center', va='bottom', fontsize=8, color=accent_color, fontweight='bold')

    # Draw Flowchart Elements

    # 1. START
    draw_capsule(5.0, 12.0, 2.6, 0.5, "START: Client Request")
    draw_arrow(5.0, 11.75, 5.0, 11.15)
    
    # 2. INGRESS
    draw_process(5.0, 10.7, 4.4, 0.9, 
                 "1. CLIENT INGRESS (ServerNode)\n• Master socket listens on Host:Port\n• Spawns worker thread to handle connection")
    draw_arrow(5.0, 10.25, 5.0, 9.65)
    
    # 3. PARSING
    draw_process(5.0, 9.2, 4.4, 0.9, 
                 "2. STREAM PARSING (HTTPRequestsNode)\n• Decodes raw socket bytes & normalizes headers\n• Extracts query parameters, cookies, and POST body")
    draw_arrow(5.0, 8.75, 5.0, 8.15)
    
    # 4. SECURITY
    draw_process(5.0, 7.7, 4.4, 0.9, 
                 "3. SECURITY MIDDLEWARE (plugins/security.py)\n• RateLimitNode evaluates request frequency limits\n• CSRFNode creates & validates tokens in database")
    draw_arrow(5.0, 7.25, 5.0, 6.65)
    
    # 5. DECISION: Is Authorized?
    draw_decision(5.0, 6.2, 2.2, 0.9, "Is\nAuthorized?")
    draw_arrow(5.0, 5.75, 5.0, 5.15, label_text="Yes", label_pos='side_yes')
    draw_arrow(6.1, 6.2, 6.6, 6.2, label_text="No", label_pos='top_no')
    
    # 5a. SECURITY ERROR BLOCK
    draw_process(8.1, 6.2, 3.0, 0.9, 
                 "SECURITY ERROR (403/429)\n• Client rate limit exceeded or CSRF mismatch\n• Halts execution and returns error page", 
                 fill_color=bg_error)
    
    # 6. ROUTING
    draw_process(5.0, 4.7, 4.4, 0.9, 
                 "4. ROUTE BRANCHING (RouterNode)\n• Matches requested URL path against route regexes\n• Validates HTTP method (GET, POST, etc.) constraints")
    draw_arrow(5.0, 4.25, 5.0, 3.65, label_text="Yes", label_pos='side_yes')
    draw_arrow(6.1, 3.2, 6.6, 3.2, label_text="No", label_pos='top_no') # connects Decision 2 to Error
    
    # 7. DECISION: Route Found?
    draw_decision(5.0, 3.2, 2.2, 0.9, "Route\nFound?")
    draw_arrow(5.0, 2.75, 5.0, 2.15, label_text="Yes", label_pos='side_yes')
    
    # 7a. ROUTING ERROR BLOCK
    draw_process(8.1, 3.2, 3.0, 0.9, 
                 "ROUTING ERROR (404/405)\n• Path not registered or method disallowed\n• Redirects to default error handler page", 
                 fill_color=bg_error)
    
    # 8. CONTROLLER LOGIC
    draw_process(5.0, 1.7, 4.4, 0.9, 
                 "5. CONTROLLER & DATABASE (Logic & Model Nodes)\n• Executes user Python/JS scripts in isolated context\n• Fetches thread-safe connections from database pool",
                 fill_color='#F2FAF2')  # subtle green tint for success execution
    draw_arrow(5.0, 1.25, 5.0, 0.65)
    
    # 9. RENDER
    draw_process(5.0, 0.2, 4.4, 0.9, 
                 "6. VIEWS & EGRESS (Render & CSS Nodes)\n• AST safety template compiling & CSS generation\n• Injects protection scripts and dispatches HTTP bytes",
                 fill_color='#FAF6F2')  # subtle warm tint
    draw_arrow(5.0, -0.25, 5.0, -0.85)
    
    # 10. SUCCESS EGRESS
    draw_process(5.0, -1.3, 4.4, 0.9, 
                 "SUCCESS RESPONSE EGRESS\n• Returns HTTP 200 Status with content payload\n• Flushes output stream to client socket",
                 fill_color='#E2F0D9')
    draw_arrow(5.0, -1.75, 5.0, -2.25)
    
    # 11. END
    draw_capsule(5.0, -2.5, 2.6, 0.5, "END: Terminate Session")
    
    # Connection logic for errors to END
    # Arrow from Security Error bottom down to Routing Error top
    draw_arrow(8.1, 5.75, 8.1, 3.65)
    # Line from Routing Error bottom down to y = -2.5
    ax.plot([8.1, 8.1], [2.75, -2.5], color=accent_color, lw=2, zorder=2)
    # Horizontal arrow from (8.1, -2.5) to END capsule right border (6.3, -2.5)
    draw_arrow(8.1, -2.5, 6.3, -2.5)
    
    plt.tight_layout()
    output_path = os.path.join(r"c:\Users\lifel\Downloads\framework\scratch", "framework_working_flow.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print("SUCCESS: Generated flowchart framework_working_flow.png in scratch/")

if __name__ == "__main__":
    generate_workflow_diagram()
