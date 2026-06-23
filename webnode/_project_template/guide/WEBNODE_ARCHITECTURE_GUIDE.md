# 🏗️ WebNode Framework — Comprehensive Architecture Guide

Ye guide **WebNode Framework** ke naye roop ka ek poora *Deep Dive* (scan aur explanation) hai. Is documentary me har code aur har node ka relationship, unka flow, aur wo aapas me kaise jude hain—wo sab vistaar se samjhaya gaya hai.

---

## 🗺️ 1. Core Execution Flow (Connection Graph)
WebNode ek *Node-based backend framework* hai. Yahan har request ek ladi (chain) se hokar guzarti hai jismein multiple nodes aapas me connect hote hain. 

Neeche diya gaya Mermaid diagram dikhata hai ki actual framework kaise request ko flow karta hai:

```mermaid
graph TD
    classDef core fill:#3b82f6,stroke:#1e40af,stroke-width:2px,color:#fff;
    classDef security fill:#10b981,stroke:#047857,stroke-width:2px,color:#fff;
    classDef router fill:#8b5cf6,stroke:#5b21b6,stroke-width:2px,color:#fff;
    classDef logic fill:#f59e0b,stroke:#b45309,stroke-width:2px,color:#fff;
    classDef render fill:#ec4899,stroke:#be185d,stroke-width:2px,color:#fff;

    Client((Browser / Client)) --> ServerNode
    
    subgraph Core
    ServerNode:::core --> HTTPRequestsNode:::core
    end
    
    subgraph Middleware / Security Plugins
    HTTPRequestsNode --> ActionLoggerNode:::security
    ActionLoggerNode --> RateLimitNode:::security
    RateLimitNode --> AntiBotNode:::security
    AntiBotNode --> CSRFNode:::security
    end
    
    subgraph Routing Mechanism
    CSRFNode --> RouterNode:::router
    end
    
    subgraph Application Nodes
    RouterNode --> URL_A[URLNode \'/shop\']:::logic
    RouterNode --> URL_B[URLNode \'/cart\']:::logic
    
    URL_A --> Logic_A[LogicNode \(shop_logic.py\)]:::logic
    URL_B --> Logic_B[LogicNode \(cart_logic.py\)]:::logic
    
    Logic_A --> Render_A[RenderNode \'shop.html\']:::render
    Logic_B --> Render_B[RenderNode \'cart.html\']:::render
    end
    
    Render_A -.-> |Returns Response Object| ServerNode
```

---

## 📂 2. Directory Structure Overview
Har file ek specific purpose solve karti hai:
- `main.py`: Yeh wo file hai jo Node Editor GUI (browser) generate/compile karta hai. Ye poore application ka control center hai jahan saare nodes judte (connect) hain.
- `settings.py`: Global variables, database connections (`db.sqlite3` aur `db_setup.py`) aur paths store hote hain.
- `setup_project.py`: Project initialization script (jaise `.secret_key` generate karna aur environment ready karna).
- `nodes/`: Framework ke engine wale pure Python logic handlers.
- `plugins/`: Middleware scripts jaise Security ya Logging.
- `node_editor/`: Graphic GUI Editor (`index.html`, `canvas.js`, aur `node_backend.py`) jo dragging-and-dropping support deta hai.
- `static/`: "Pure Python" logic files aur global assets (`shop_logic.py`, `cart_logic.py`, etc.).
- `templates/`: HTML files (jinme Python backend ki dictionaries inject hoti hain).

---

## 🧩 3. The `nodes/` Directory (Core Engine)

### `base_node.py`
**Kaam:** Base class jisse saare nodes inherit karte hain.
**Connected to:** Sabhi nodes isi par based hain.
**Ahem functionality:** Isme ek `.connect()` function hota hai jo yeh tay karta hai ki is node ke baad agla node kaunsa execute hoga. Iska `process(data)` method hi poori chain ko data pass karta hai.

### `server_node.py`
**Kaam:** Entry point. Python ke `http.server.HTTPServer` ko aasan banata hai.
**Connected to:** `main.py` me instantiate hokar execute hota hai.
**Flow:** Jaise hi browser `/shop` mangta hai, `ServerNode` sabse pehle dekhta hai. Yeh lazily middleware execute karke request ko aage graph (`start_flow`) me bhejta hai aur aakhir me response ko serialize karke wapas browser (Client) ko bhejta hai. (Dhyan rakhein, yeh static files serving ke liye explicit MIME types bhi handle karta hai).

### `http_requests_node.py`
**Kaam:** Request Wrapper.
**Connected to:** Humesha `ServerNode` ke theek baad.
**Flow:** HTTP path, method (`GET/POST`), body form data, JSON, query params, in sabko parse karke ek aasaan `request` object (`request.url_params`, `request.get_param()`) mein pack karke aage (`plugins/` ya `RouterNode` ko) refer karta hai.

### `route_node.py` (RouterNode)
**Kaam:** The Junction Box (Y-Splitter).
**Connected to:** Iske andar kai (multiple) `URLNode`s (branches) feed kiye jate hain.
**Flow:** Yeh request branch karke sabse pehla `URLNode` dudndhta hai jo requested path se match ho. Agar match hota hai, request us branch me aage chali jati hai. Yeh file automatically generate hoti hai WebNode UI dwara.

### `url_node.py`
**Kaam:** Path Matcher.
**Flow:** Yeh node check karta hai ki path user ki request match kar raha hai ya nahi (eg. `/product/<id>`). Match hone pe yeh `<id>` extract karke `request.url_params` me daal deta hai and `LogicNode` ko call karta hai. Agar match nahi hua to `None` return karta hai, taaki `RouterNode` aage doosre raste pe mud sake.

### `logic_node.py`
**Kaam:** User ka Data Processing Code.
**Connected to:** Frontend Logic.
**Flow:** Yeh `static/shop_logic.py` ke python functions ko call karta hai. Yaha aapka DB Query, math calculations, authentication wagera hota hai. Return ek dictionary honi chahiye (jaise `{'products': products}`). WebNode GUI isi LogicNode textarea me code dikhata hai.

### `template_node.py` (RenderNode)
**Kaam:** HTML Renderer and PyScript Auto-Injector.
**Connected to:** `LogicNode` ke baad.
**Flow:** Yeh `templates/*.html` path padhta hai, usme `LogicNode` se aayi dictionary inject karta hai (using `{{ var }}`). Yeh ek special framework feature rakhta hai: agar HTML me `<script type="py">` ya `py-click` dikha, toh yeh chupchap background me PyScript Engine include kar dega (Layer 8)! 

### `response.py`
**Kaam:** Structured HTTP responses (Redirects, JSON, Not Found, Forbidden).
**Connected to:** Any Node (but generally Logic nodes return it if they want to override standard HTML rendering). 

---

## 🔒 4. The `plugins/` Directory (Security & Middleware)
Middlewares Request cycle ke theek baad lagte hain, aur inki output ko pass/block karne ki authority hoti hai.

1. **`ActionLoggerNode` (logger.py)**: Har hit aur request data ko JSONL file me log karta hai (analytics ke liye). Path: `core/logs/requests/`.
2. **`RateLimitNode` (security.py)**: Ek IP ko limited request `/sec` filter deta hai. Spam roknay ke liye 429 Too Many Requests bhejta hai.
3. **`AntiBotNode`**: "curl", "python-requests" jaise headless user-agents block karke scrapers rokta hai.
4. **`CSRFNode`**: Forms aur data mutation ko protect karta hai. Real `secrets` backend se tokens generate hote hain jo context me aate hain (aur form HTML check karta hai). Bina Token koi POST complete nahi ho sakti.
5. **`ScreenProtectionNode`**: (Optional) JavaScript inject karke Screenshots nikaalne aur Copying/Inspecting ko HTML level pe hide kar deta hai.

---

## 🖥️ 5. Default App (Static Logic & Templates)
Ye wahi files hain jo eCommerce logic banate hain. Node Editor se ye directly link ki gayi hain (ab yeh `graph.json` ke andar inline hai taaki visual GUI se direct edit ki ja sake):
- **`cart_logic.py`**, **`checkout_logic.py`**, **`shop_logic.py`**, **`api_logic.py`**: Ye DB interactions handle karte hain (SQLite `products` table). 
- **Pure Python Concept**: Is framework mein JS aur external API requests avoid ki gayi hain. UI interaction server-side functions ke zariye hoti hai.

---

## ⚙️ 6. The WebNode GUI Editor (`node_editor/`)
Yeh is poore framework ka USP hai.

- **`index.html` & `canvas.js` & `styles.css`**: Ye teeno milkar ek web-based Monaco-powered Drag n Drop GUI system banate hain jaha aap naye nodes add karke URL aur Logic flow wire kar sakte hain.
- **`node_backend.py`**: Yeh khud ek separate `server` hai (port 8080) jo sirf GUI ke liye chalta hai. 
  - **`handle_save()`**: Canvas se naye banaye graph ko `graph.json` mein save karta hai.
  - **`handle_deploy()`** (`compile_graph` function): Ye function `graph.json` ko padhta hai aur reverse engineering karke poora `main.py` python script regenerate karta hai! `node_backend.py` actual framework server ko memory restart/boot kar deta hai taaki code deploy ho sake. Isme MIME type Windows network bugs ko permanently resolve kiya gaya hai.

---

## 📝 7. Final Summary
Aapka framework simple HTML render karke `main.py` pe poora routing handle karta hai. Jisse aap server restart kare bina node_editor UI ke through complex Logic graph bana sakte hain, edit kar sakte hain aur Deploy par click karte hi website live update ho jati hai.
