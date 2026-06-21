import json
import os

RAM_TRADERS_DIR = "c:/Users/lifel/Downloads/ApnaShop/ApnaShop/RamTraders"
FRAMEWORK_DIR = "c:/Users/lifel/Downloads/framework/node_editor"

def read_file(filename):
    with open(os.path.join(RAM_TRADERS_DIR, filename), 'r', encoding='utf-8') as f:
        return f.read()

def generate_graph():
    nodes = []
    connections = []
    
    # 1. Core nodes
    nodes.append({
        "id": "server-1",
        "type": "ServerNode",
        "x": -400,
        "y": 0,
        "config": {
            "ip": "127.0.0.1",
            "port": 8000
        }
    })
    
    nodes.append({
        "id": "http-1",
        "type": "HTTPRequestsNode",
        "x": -100,
        "y": 0,
        "config": {}
    })
    
    connections.append({"source": "server-1", "target": "http-1"})
    
    # 2. Pages
    pages = [
        {"path": "/", "filename": "index.html", "y": -200, "id_suffix": "index"},
        {"path": "/login.html", "filename": "login.html", "y": 0, "id_suffix": "login"},
        {"path": "/admin.html", "filename": "admin.html", "y": 200, "id_suffix": "admin"}
    ]
    
    css_code = read_file("traders.css")
    js_code = read_file("script.js")
    
    nodes.append({
        "id": "css-1",
        "type": "CSSNode",
        "x": 800,
        "y": 0,
        "config": {
            "css_filename": "traders.css",
            "css_code": css_code
        }
    })
    
    nodes.append({
        "id": "js-1",
        "type": "JSNode",
        "x": 800,
        "y": 200,
        "config": {
            "filename": "script.js",
            "code": js_code
        }
    })
    
    for page in pages:
        url_id = f"url-{page['id_suffix']}"
        render_id = f"render-{page['id_suffix']}"
        
        html_content = read_file(page["filename"])
        
        nodes.append({
            "id": url_id,
            "type": "URLNode",
            "x": 200,
            "y": page["y"],
            "config": {
                "path": page["path"]
            }
        })
        
        nodes.append({
            "id": render_id,
            "type": "RenderNode",
            "x": 500,
            "y": page["y"],
            "config": {
                "filename": page["filename"],
                "html_code": html_content
            }
        })
        
        connections.append({"source": "http-1", "target": url_id})
        connections.append({"source": url_id, "target": render_id})
        connections.append({"source": render_id, "target": "css-1"})
        connections.append({"source": render_id, "target": "js-1"})
    
    # 3. API Database Endpoints
    # For simplicity, we create a few critical API endpoints since porting all takes too much space
    # Let's add /api/products
    url_api_products = "url-api-products"
    model_products = "model-products"
    logic_products = "logic-products"
    
    nodes.append({
        "id": url_api_products,
        "type": "URLNode",
        "x": 200,
        "y": 400,
        "config": {
            "path": "/api/products"
        }
    })
    
    nodes.append({
        "id": model_products,
        "type": "ModelNode",
        "x": 500,
        "y": 400,
        "config": {
            "query": "SELECT * FROM products",
            "paramsMap": "",
            "contextKey": "products",
            "isWrite": False
        }
    })
    
    logic_code = """def process_logic(request):
    import json
    products = request.context.get('products', [])
    parsed_products = []
    for p in products:
        try:
            images = json.loads(p.get('images', '[]'))
        except:
            images = []
        if not images and p.get('image'):
            images = [p['image']]
        
        thumbnails = images if len(images) > 0 else [p.get('image'), "./material1.webp", "./material2.webp"]
        
        try:
            highlights = json.loads(p.get('highlights', '[]'))
        except:
            highlights = []
            
        try:
            specs = json.loads(p.get('specs', '{}'))
        except:
            specs = {}
            
        parsed_products.append({
            **p,
            'thumbnails': thumbnails,
            'highlights': highlights,
            'specs': specs
        })
    
    from nodes.response import Response
    return Response(body=json.dumps(parsed_products), status_code=200, headers={"Content-Type": "application/json"})
"""
    
    nodes.append({
        "id": logic_products,
        "type": "LogicNode",
        "x": 800,
        "y": 400,
        "config": {
            "code": logic_code
        }
    })
    
    connections.append({"source": "http-1", "target": url_api_products})
    connections.append({"source": url_api_products, "target": model_products})
    connections.append({"source": model_products, "target": logic_products})
    
    graph_data = {
        "nodes": nodes,
        "connections": connections
    }
    
    with open(os.path.join(FRAMEWORK_DIR, 'graph.json'), 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=4)
        
    print("Graph JSON created successfully at", os.path.join(FRAMEWORK_DIR, 'graph.json'))

if __name__ == "__main__":
    generate_graph()
