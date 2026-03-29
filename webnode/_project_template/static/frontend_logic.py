from pyscript import document, window

def change_text(event):
    # Get the HTML element by ID
    text_box = document.getElementById("demo-text")
    
    # Change its content just like JS's innerText
    text_box.innerText = "Wow! HTML widget updated from a Static Python File! 🚀"
    
    # Change styling dynamically
    text_box.style.color = "#10b981"  # Emerald green
    text_box.style.fontWeight = "bold"

def show_alert(event):
    # Call JS functions directly from Python if needed
    window.alert("Hello from Python Logic in static folder!")