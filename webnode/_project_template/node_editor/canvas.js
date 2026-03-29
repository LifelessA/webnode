// State
let panX = 0, panY = 0, scale = 1;
let isPanning = false, startX, startY;
let activeNode = null;
let isWiring = false;
let startPort = null;
let wires = [];
let nodeIdCounter = 10; // Reserve < 10 for defaults

const canvasLayer = document.getElementById('canvas-layer');
const canvasContainer = document.getElementById('canvas-container');
const wireLayer = document.getElementById('wire-layer');

// --- Initialization ---
function init() {
    // Bind existing nodes
    document.querySelectorAll('#canvas-layer .node').forEach(node => bindNodeEvents(node));
    updateAllWires();

    // Create the floating wire disconnect button (once)
    _createWireDisconnectBtn();

    // Bind wire dblclick deletion (legacy fallback)
    wireLayer.addEventListener('dblclick', (e) => {
        if (e.target.classList.contains('wire')) {
            deleteWireByPath(e.target);
        }
    });

    // Load graph automatically
    loadGraphJSON();
}

// --- Panning & Zooming ---
canvasContainer.addEventListener('mousedown', (e) => {
    if (e.target.closest('.node') || e.target.closest('.port')) return;
    if (e.button === 1 || e.button === 0) {
        isPanning = true;
        startX = e.clientX - panX;
        startY = e.clientY - panY;
    }
});

window.addEventListener('mousemove', (e) => {
    if (isPanning) {
        panX = e.clientX - startX;
        panY = e.clientY - startY;
        updateCanvasTransform();
    }
    if (isWiring && startPort) {
        drawTempWire(e.clientX, e.clientY);
    }
});

window.addEventListener('mouseup', () => {
    isPanning = false;
    stopWiring();
});

canvasContainer.addEventListener('wheel', (e) => {
    // Only zoom when Ctrl (Windows/Linux) or Cmd (macOS) is pressed
    if (e.ctrlKey || e.metaKey) {
        e.preventDefault();

        // Zoom sensitivity: 5% per scroll step
        const zoomIntensity = 0.05;
        // Scroll up (negative deltaY) => zoom in, down => zoom out
        const delta = e.deltaY > 0 ? -1 : 1;
        let factor = Math.exp(delta * zoomIntensity);
        let newScale = scale * factor;
        newScale = Math.min(Math.max(0.2, newScale), 3);
        if (newScale === scale) return;

        // Get mouse position relative to the canvas container
        const rect = canvasContainer.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        // Compute the canvas (unscaled) coordinates of the point under the mouse
        const canvasX = (mouseX - panX) / scale;
        const canvasY = (mouseY - panY) / scale;

        // Apply the new scale
        scale = newScale;

        // Adjust pan so that the same canvas point stays under the mouse
        panX = mouseX - canvasX * scale;
        panY = mouseY - canvasY * scale;

        // Apply the transformation and redraw wires
        updateCanvasTransform();
    }
});

function updateCanvasTransform() {
    canvasLayer.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
    canvasContainer.style.backgroundPosition = `${panX}px ${panY}px`;
    canvasContainer.style.backgroundSize = `${20 * scale}px ${20 * scale}px`;
    updateAllWires();
}

// --- Dynamic Node Event Binding ---
function bindNodeEvents(node) {
    // Bind drag on node-header
    const header = node.querySelector('.node-header');
    if (header) {
        header.addEventListener('mousedown', startNodeDrag);
    }

    node.querySelectorAll('.port').forEach(port => {
        port.addEventListener('mousedown', onPortMouseDown);
        port.addEventListener('mouseup', onPortMouseUp);
    });

    // ── Inject X delete button (if not already present) ──
    if (!node.querySelector('.node-delete-btn')) {
        const btn = document.createElement('button');
        btn.className = 'node-delete-btn';
        btn.title = 'Delete node';
        btn.textContent = '✕';
        btn.addEventListener('mousedown', e => e.stopPropagation()); // don't start drag
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteNode(node.id);
        });
        node.appendChild(btn);
    }
}

// --- Deletion Handlers ---
function deleteNode(nodeId) {
    const nodeEl = document.getElementById(nodeId);
    if (!nodeEl) return;

    wires = wires.filter(w => {
        if (w.sourceNode === nodeId || w.targetNode === nodeId) {
            w.path.remove();
            return false;
        }
        return true;
    });

    nodeEl.remove();
}

function deleteWire(wireObj) {
    if (!wireObj) return;
    wires = wires.filter(w => {
        if (w === wireObj) {
            w.path.remove();
            return false;
        }
        return true;
    });
}

// Keep backward compat for dblclick wire delete
function deleteWireByPath(pathEl) {
    const wireObj = wires.find(w => w.path === pathEl);
    deleteWire(wireObj);
}

// ─── Wire Hover Disconnect Button ────────────────────────────────────────────
let _hoveredWire = null;

function _createWireDisconnectBtn() {
    if (document.getElementById('wire-disconnect-btn')) return;
    const btn = document.createElement('button');
    btn.id = 'wire-disconnect-btn';
    btn.title = 'Disconnect wire';
    btn.textContent = '−';
    btn.addEventListener('click', () => {
        if (_hoveredWire) {
            deleteWire(_hoveredWire);
            _hoveredWire = null;
            btn.style.display = 'none';
        }
    });
    // Keep visible while hovering the button itself
    btn.addEventListener('mouseenter', () => { btn.style.display = 'flex'; });
    btn.addEventListener('mouseleave', () => { btn.style.display = 'none'; _hoveredWire = null; });
    canvasContainer.appendChild(btn);
}

function _getBezierMidpoint(x1, y1, x2, y2) {
    // Midpoint of the cubic bezier used in drawBezier()
    const curvature = Math.abs(x2 - x1) * 0.5;
    // Cubic bezier: B(0.5) for P0,P1,P2,P3 where P1=(x1+c,y1) P2=(x2-c,y2)
    const t = 0.5;
    const mt = 1 - t;
    const cx1 = x1 + curvature, cy1 = y1;
    const cx2 = x2 - curvature, cy2 = y2;
    return {
        x: mt * mt * mt * x1 + 3 * mt * mt * t * cx1 + 3 * mt * t * t * cx2 + t * t * t * x2,
        y: mt * mt * mt * y1 + 3 * mt * mt * t * cy1 + 3 * mt * t * t * cy2 + t * t * t * y2,
    };
}

function bindWireHover(wireObj) {
    const path = wireObj.path;
    path.style.pointerEvents = 'stroke';
    path.style.cursor = 'pointer';

    path.addEventListener('mouseenter', () => {
        _hoveredWire = wireObj;
        const btn = document.getElementById('wire-disconnect-btn');
        if (!btn) return;

        // Calculate midpoint in canvasContainer coordinates
        const start = getPortCoords(wireObj.fromEl);
        const end = getPortCoords(wireObj.toEl);
        const mid = _getBezierMidpoint(start.x, start.y, end.x, end.y);

        btn.style.left = `${mid.x}px`;
        btn.style.top = `${mid.y}px`;
        btn.style.display = 'flex';
    });

    path.addEventListener('mouseleave', (e) => {
        // Don't hide if moving to the button itself
        const btn = document.getElementById('wire-disconnect-btn');
        if (btn && e.relatedTarget === btn) return;
        if (btn) btn.style.display = 'none';
        _hoveredWire = null;
    });
}


// --- Drag & Drop from Palette ---
document.querySelectorAll('.palette-node').forEach(item => {
    item.addEventListener('dragstart', (e) => {
        e.dataTransfer.setData('text/plain', e.target.getAttribute('data-type'));
    });
});

canvasContainer.addEventListener('dragover', (e) => {
    e.preventDefault();
});

canvasContainer.addEventListener('drop', (e) => {
    e.preventDefault();
    const nodeType = e.dataTransfer.getData('text/plain');
    if (!nodeType) return;

    const template = document.querySelector(`#node-templates [data-type="${nodeType}"]`);
    if (!template) return;

    const newNode = template.cloneNode(true);
    const newId = `node-${nodeIdCounter++}`;
    newNode.id = newId;

    newNode.querySelectorAll('.port').forEach(port => {
        port.dataset.node = newId;
    });

    // Get mouse position relative to canvas container
    const rect = canvasContainer.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // Convert to canvas (unscaled) coordinates using current pan and scale
    const canvasX = (mouseX - panX) / scale;
    const canvasY = (mouseY - panY) / scale;

    // Set initial position
    newNode.style.left = `${canvasX}px`;
    newNode.style.top = `${canvasY}px`;

    canvasLayer.appendChild(newNode);
    bindNodeEvents(newNode);

    // Store intended position for safety check
    newNode.dataset.intendedX = canvasX;
    newNode.dataset.intendedY = canvasY;

    if (['LogicNode', 'ContextNode', 'RenderNode', 'CSSNode'].includes(nodeType)) {
        initMonacoEditor(newNode, nodeType);
    }

    // Safety: after a short delay, reapply position if it changed
    setTimeout(() => {
        if (newNode.parentNode) {
            const currentX = parseFloat(newNode.style.left);
            const currentY = parseFloat(newNode.style.top);
            // If node moved more than 1px, reset to intended coordinates
            if (Math.abs(currentX - canvasX) > 1 || Math.abs(currentY - canvasY) > 1) {
                newNode.style.left = `${canvasX}px`;
                newNode.style.top = `${canvasY}px`;
                updateAllWires();
            }
        }
    }, 500);
});

// --- Monaco Editor ---
function initMonacoEditor(nodeElement, type) {
    const container = nodeElement.querySelector('.monaco-container');
    if (!container) return;

    let initConfig = {
        value: '',
        language: 'python',
        theme: 'vs-dark',
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        fontSize: 12
    };

    if (type === 'LogicNode') {
        initConfig.value = `def process_logic(request):
    # Write Python logic here
    # e.g., request.context["result"] = "<h1>Hello</h1>"
    return {}`;
    } else if (type === 'ContextNode') {
        initConfig.value = `def node_logic(request):
    # Add global variables here
    return {"key": "value"}`;
    } else if (type === 'RenderNode') {
        initConfig.value = `<!DOCTYPE html>
<html lang="en">
<head>
    <title>Document</title>
</head>
<body>
    {result}
</body>
</html>`;
        initConfig.language = 'html';
    } else if (type === 'CSSNode') {
        initConfig.value = `/* CSS styles for your page */\nbody {\n    font-family: sans-serif;\n    margin: 0;\n    padding: 0;\n}\n\n.container {\n    max-width: 1200px;\n    margin: 0 auto;\n    padding: 20px;\n}`;
        initConfig.language = 'css';
    }

    if (window.require) {
        require(['vs/editor/editor.main'], function () {
            const editor = monaco.editor.create(container, initConfig);
            nodeElement._monacoEditor = editor;

            const resizeObserver = new ResizeObserver(() => editor.layout());
            resizeObserver.observe(container);
        });
    }
}

// --- Node Dragging (Canvas) ---
function startNodeDrag(e) {
    if (e.target.classList.contains('port') ||
        e.target.classList.contains('in-port') ||
        e.target.classList.contains('out-port')) return;

    const node = e.target.closest('.node');
    if (!node) return;
    activeNode = node;
    
    // Use z-index instead of appendChild to prevent Monaco editor from detaching/breaking
    let maxZ = 10;
    document.querySelectorAll('#canvas-layer .node').forEach(n => {
        let z = parseInt(n.style.zIndex || 10);
        if (z > maxZ) maxZ = z;
    });
    activeNode.style.zIndex = maxZ + 1;

    // Use node's current CSS position — works correctly at any zoom level
    const startNodeX = parseFloat(activeNode.style.left) || 0;
    const startNodeY = parseFloat(activeNode.style.top) || 0;
    const startMouseX = e.clientX;
    const startMouseY = e.clientY;

    function onMouseMove(moveEvent) {
        // Delta in screen pixels, divide by scale to get canvas-space delta
        const dx = (moveEvent.clientX - startMouseX) / scale;
        const dy = (moveEvent.clientY - startMouseY) / scale;
        activeNode.style.left = `${startNodeX + dx}px`;
        activeNode.style.top = `${startNodeY + dy}px`;
        
        // Only update wires connected to the active node to prevent layout thrashing
        wires.forEach(wire => {
            if (wire.sourceNode === activeNode.id || wire.targetNode === activeNode.id) {
                const start = getPortCoords(wire.fromEl);
                const end = getPortCoords(wire.toEl);
                drawBezier(wire.path, start.x, start.y, end.x, end.y);
            }
        });
    }

    function onMouseUp() {
        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('mouseup', onMouseUp);
        activeNode = null;
    }

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    e.preventDefault();
}

// --- Wiring (SVGs) ---
function onPortMouseDown(e) {
    e.stopPropagation();
    isWiring = true;
    startPort = e.target;

    const tempPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    tempPath.classList.add('wire');
    tempPath.id = 'temp-wire';
    wireLayer.appendChild(tempPath);
}

function onPortMouseUp(e) {
    if (isWiring && startPort && startPort !== e.target) {
        const isStartOut = startPort.classList.contains('out-port');
        const isEndIn = e.target.classList.contains('in-port');

        if (isStartOut && isEndIn && startPort.dataset.node !== e.target.dataset.node) {
            createWire(startPort, e.target);
        }
    }
}

function stopWiring() {
    isWiring = false;
    startPort = null;
    const temp = document.getElementById('temp-wire');
    if (temp) temp.remove();
}

function getPortCoords(portEl) {
    const rect = portEl.getBoundingClientRect();
    const canvasRect = canvasContainer.getBoundingClientRect();
    return {
        x: rect.left - canvasRect.left + (rect.width / 2),
        y: rect.top - canvasRect.top + (rect.height / 2)
    };
}

function drawTempWire(mouseX, mouseY) {
    if (!startPort) return;
    const start = getPortCoords(startPort);
    const canvasRect = canvasContainer.getBoundingClientRect();
    const endX = mouseX - canvasRect.left;
    const endY = mouseY - canvasRect.top;

    drawBezier(document.getElementById('temp-wire'), start.x, start.y, endX, endY);
}

function createWire(fromPort, toPort) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.classList.add('wire');
    wireLayer.appendChild(path);

    const wireObj = {
        sourceNode: fromPort.dataset.node,
        sourcePort: fromPort.dataset.port,
        targetNode: toPort.dataset.node,
        targetPort: toPort.dataset.port,
        path: path,
        fromEl: fromPort,
        toEl: toPort
    };
    wires.push(wireObj);
    bindWireHover(wireObj);   // ← hover disconnect button
    updateAllWires();
}

function updateAllWires() {
    wires.forEach(wire => {
        const start = getPortCoords(wire.fromEl);
        const end = getPortCoords(wire.toEl);
        drawBezier(wire.path, start.x, start.y, end.x, end.y);
    });
}

function drawBezier(pathEl, x1, y1, x2, y2) {
    const curvature = Math.abs(x2 - x1) * 0.5;
    const d = `M ${x1} ${y1} C ${x1 + curvature} ${y1}, ${x2 - curvature} ${y2}, ${x2} ${y2}`;
    pathEl.setAttribute('d', d);
}

// --- Graph Serialization & Deserialization ---

function waitForMonacoEditors(
    timeout = 3000
) {
    return new Promise(resolve => {
        const start = Date.now();
        const check = setInterval(() => {
            // Check all monaco containers
            const pending = document
                .querySelectorAll(
                    '.monaco-container'
                );

            // All loaded if every container
            // either has no editor needed
            // OR has _monacoEditor attached
            const allReady = Array.from(
                pending
            ).every(el => {
                const node = el.closest(
                    '.node'
                );
                if (!node) return true;
                const type = node.dataset.type;
                const needsEditor = [
                    'LogicNode',
                    'ContextNode',
                    'RenderNode',
                    'CSSNode'
                ].includes(type);
                return !needsEditor ||
                    !!node._monacoEditor;
            });

            if (allReady) {
                clearInterval(check);
                resolve();
                return;
            }

            // Timeout fallback
            if (Date.now() - start > timeout) {
                clearInterval(check);
                resolve(); // resolve anyway
            }
        }, 50);
    });
}

async function loadGraphJSON() {
    try {
        const res = await fetch('/api/load');
        const data = await res.json();

        if (!data?.nodes?.length) return;

        // Clear canvas
        document.querySelectorAll(
            '#canvas-layer .node'
        ).forEach(n => n.remove());
        document.querySelectorAll(
            '#wire-layer .wire'
        ).forEach(w => w.remove());
        wires = [];

        let maxId = 10;

        // Step 1: Create ALL nodes first
        data.nodes.forEach(nodeData => {
            const template = document
                .querySelector(
                    '#node-templates ' +
                    '[data-type="' +
                    nodeData.type + '"]'
                );
            if (!template) return;

            const newNode =
                template.cloneNode(true);
            newNode.id = nodeData.id;

            const nId = parseInt(
                nodeData.id.replace('node-', '')
            );
            if (!isNaN(nId) && nId > maxId)
                maxId = nId;

            newNode.querySelectorAll(
                '.port'
            ).forEach(port => {
                port.dataset.node = nodeData.id;
            });

            newNode.style.left =
                `${nodeData.x}px`;
            newNode.style.top =
                `${nodeData.y}px`;

            canvasLayer.appendChild(newNode);
            bindNodeEvents(newNode);

            // Init Monaco editors
            if (['LogicNode',
                'ContextNode',
                'RenderNode'].includes(
                    nodeData.type
                )) {
                initMonacoEditor(
                    newNode,
                    nodeData.type
                );
            }
        });

        nodeIdCounter = maxId + 1;

        // Step 2: Wait for Monaco editors
        await waitForMonacoEditors();

        // Step 3: Load config values
        // (guaranteed safe now)
        data.nodes.forEach(nodeData => {
            const nodeEl = document
                .getElementById(nodeData.id);
            if (!nodeEl) return;

            const config = nodeData.config
                || {};
            const type = nodeData.type;

            if (type === 'ServerNode') {
                if (config.ip)
                    nodeEl.querySelector(
                        '.ip-input'
                    ).value = config.ip;
                if (config.port)
                    nodeEl.querySelector(
                        '.port-input'
                    ).value = config.port;
            } else if (type === 'URLNode') {
                if (config.path)
                    nodeEl.querySelector(
                        '.path-input'
                    ).value = config.path;
            } else if (type === 'ModelNode') {
                if (config.query)
                    nodeEl.querySelector(
                        '.query-input'
                    ).value = config.query;
                if (config.paramsMap)
                    nodeEl.querySelector(
                        '.params-input'
                    ).value = config.paramsMap;
                if (config.contextKey)
                    nodeEl.querySelector(
                        '.context-input'
                    ).value = config.contextKey;
                if (config.isWrite !==
                    undefined)
                    nodeEl.querySelector(
                        '.is-write-input'
                    ).checked = config.isWrite;
            } else if (type === 'RenderNode') {
                if (config.filename)
                    nodeEl.querySelector(
                        '.filename-input'
                    ).value = config.filename;
                if (config.html_code &&
                    nodeEl._monacoEditor)
                    nodeEl._monacoEditor
                        .setValue(
                            config.html_code
                        );
            } else if (
                type === 'LogicNode' ||
                type === 'ContextNode'
            ) {
                if (config.code &&
                    nodeEl._monacoEditor)
                    nodeEl._monacoEditor
                        .setValue(config.code);
            } else if (type === 'CSSNode') {
                if (config.css_filename)
                    nodeEl.querySelector(
                        '.css-filename-input'
                    ).value = config.css_filename;
                if (config.css_code &&
                    nodeEl._monacoEditor)
                    nodeEl._monacoEditor
                        .setValue(config.css_code);
            }
        });

        // Step 4: Draw connections
        // (guaranteed: nodes + editors ready)
        data.connections.forEach(conn => {
            const sourceEl = document
                .getElementById(conn.source);
            const targetEl = document
                .getElementById(conn.target);

            if (!sourceEl || !targetEl) {
                console.warn(
                    'Missing node for ' +
                    'connection:',
                    conn.source,
                    '->',
                    conn.target
                );
                return;
            }

            const fromPort = sourceEl
                .querySelector('.out-port');
            const toPort = targetEl
                .querySelector('.in-port');

            if (fromPort && toPort) {
                createWire(fromPort, toPort);
            }
        });

        updateAllWires();

    } catch (e) {
        console.error(
            'Failed to load graph:', e
        );
    }
}

// --- Serialization & Backend API ---
function extractGraphJSON() {
    const nodes = [];
    document.querySelectorAll('#canvas-layer .node').forEach(nodeEl => {
        const id = nodeEl.id;
        const type = nodeEl.dataset.type;
        const x = parseFloat(nodeEl.style.left) || 0;
        const y = parseFloat(nodeEl.style.top) || 0;

        let config = {};
        if (type === 'ServerNode') {
            config.ip = nodeEl.querySelector('.ip-input').value;
            config.port = parseInt(nodeEl.querySelector('.port-input').value, 10);
        } else if (type === 'URLNode') {
            config.path = nodeEl.querySelector('.path-input').value;
        } else if (type === 'RenderNode') {
            config.filename = nodeEl.querySelector('.filename-input').value;
            if (nodeEl._monacoEditor) {
                config.html_code = nodeEl._monacoEditor.getValue();
            }
        } else if (type === 'ModelNode') {
            config.query = nodeEl.querySelector('.query-input').value;
            config.paramsMap = nodeEl.querySelector('.params-input').value;
            config.contextKey = nodeEl.querySelector('.context-input').value;
            config.isWrite = nodeEl.querySelector('.is-write-input').checked;
        } else if (type === 'LogicNode' || type === 'ContextNode') {
            if (nodeEl._monacoEditor) {
                config.code = nodeEl._monacoEditor.getValue();
            }
        } else if (type === 'CSSNode') {
            config.css_filename = nodeEl.querySelector('.css-filename-input').value;
            if (nodeEl._monacoEditor) {
                config.css_code = nodeEl._monacoEditor.getValue();
            }
        }

        nodes.push({ id, type, x, y, config });
    });

    const connections = wires.map(w => ({
        source: w.sourceNode,
        target: w.targetNode
    }));

    return { nodes, connections };
}

// Bind Toolbar Buttons
document.getElementById('btn-save').addEventListener('click', async () => {
    const payload = extractGraphJSON();
    console.log("Saving graph:", payload);
    try {
        await fetch('/api/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        alert('Graph JSON saved locally!');
    } catch (e) {
        alert('Failed to save. Is node_backend.py running?');
    }
});

document.getElementById('btn-deploy').addEventListener('click', async () => {
    const payload = extractGraphJSON();
    try {
        const res = await fetch('/api/deploy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (result.status === 'success') {
            document.getElementById('status-indicator').innerText = '● Live';
            document.getElementById('status-indicator').className = 'live';
            alert('Deployed successfully! main.py generated and server is running.');
        } else {
            alert('Failed to deploy: ' + result.message);
        }
    } catch (e) {
        alert('Cannot connect to backend compiler.');
    }
});

document.getElementById('btn-stop').addEventListener('click', async () => {
    try {
        await fetch('/api/stop', { method: 'POST' });
        document.getElementById('status-indicator').innerText = '● Offline';
        document.getElementById('status-indicator').className = '';
    } catch (e) { }
});

document.getElementById('btn-clear').addEventListener('click', () => {
    document.querySelectorAll('#canvas-layer .node').forEach(n => n.remove());
    document.querySelectorAll('#wire-layer .wire').forEach(w => w.remove());
    wires = [];
    nodeIdCounter = 10;
});

// --- Polling & Flow Traversal ---
async function pollServerStatus() {
    try {
        const [statusRes, errorsRes] = await Promise.all([
            fetch('/api/status'),
            fetch('/api/errors').catch(() => null)
        ]);

        const data = await statusRes.json();
        const errorState = errorsRes ? await errorsRes.json().catch(() => ({})) : {};

        const isLive = (data.status === 'live');
        updateVisualFlow(isLive);
        updateNodeErrors(errorState);

        const indicator = document.getElementById('status-indicator');
        if (isLive) {
            indicator.innerText = '● Live';
            indicator.className = 'live';
        } else {
            indicator.innerText = '● Offline';
            indicator.className = '';
        }
    } catch (e) {
        updateVisualFlow(false);
    }
}

function updateNodeErrors(errorState) {
    // Clear all previous error states first
    document.querySelectorAll('#canvas-layer > .node.status-error').forEach(n => {
        n.classList.remove('status-error');
        const tip = n.querySelector('.__err-tip');
        if (tip) tip.remove();
    });

    // No errors
    if (!errorState || Object.keys(errorState).length === 0) return;

    // For each errored node_type, find matching nodes on canvas and highlight red
    Object.values(errorState).forEach(err => {
        const nodeType = err.node_type;
        document.querySelectorAll(`#canvas-layer > .node[data-type="${nodeType}"]`).forEach(nodeEl => {
            nodeEl.classList.add('status-error');

            // Add error tooltip if not already present
            if (!nodeEl.querySelector('.__err-tip')) {
                const tip = document.createElement('div');
                tip.className = '__err-tip';
                tip.textContent = `⚠ ${err.error_type}: ${err.message}`;
                tip.style.cssText = `
                    position:absolute; bottom:-32px; left:50%; transform:translateX(-50%);
                    background:#f43f5e; color:#fff; font-size:11px; padding:3px 8px;
                    border-radius:6px; white-space:nowrap; z-index:999;
                    pointer-events:none; max-width:260px; overflow:hidden;
                    text-overflow:ellipsis;
                `;
                nodeEl.style.position = 'relative';
                nodeEl.appendChild(tip);
            }
        });
    });
}

function updateVisualFlow(isLive) {
    const allNodes = document.querySelectorAll('#canvas-layer > .node');

    allNodes.forEach(n => {
        n.classList.remove('status-green');
        n.classList.add('status-red');
    });
    wires.forEach(w => {
        w.path.classList.remove('active');
        w.path.classList.add('error');
    });

    if (!isLive) return;

    let serverNodeEl = null;
    for (let i = 0; i < allNodes.length; i++) {
        if (allNodes[i].dataset.type === 'ServerNode') {
            serverNodeEl = allNodes[i];
            break;
        }
    }

    if (!serverNodeEl) return;

    const reachableNodes = new Set();
    const reachableWires = new Set();

    reachableNodes.add(serverNodeEl.id);
    const queue = [serverNodeEl.id];

    while (queue.length > 0) {
        const curr = queue.shift();
        wires.forEach(w => {
            if (w.sourceNode === curr) {
                reachableWires.add(w);
                if (!reachableNodes.has(w.targetNode)) {
                    reachableNodes.add(w.targetNode);
                    queue.push(w.targetNode);
                }
            }
        });
    }

    allNodes.forEach(n => {
        if (reachableNodes.has(n.id)) {
            n.classList.remove('status-red');
            n.classList.add('status-green');
        }
    });

    wires.forEach(w => {
        if (reachableWires.has(w)) {
            w.path.classList.remove('error');
            w.path.classList.add('active');
        }
    });
}

setInterval(pollServerStatus, 2000);

// Start
init();