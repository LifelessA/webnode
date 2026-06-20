
function wrap3D(btn, text) {
    btn.innerHTML = `<span class="shadow"></span><span class="edge"></span><span class="front">${text}</span>`;
}
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
        wrap3D(btn, '✕');
        btn.addEventListener('mousedown', e => e.stopPropagation()); // don't start drag
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteNode(node.id);
        });
        node.appendChild(btn);
    }

    // ── Bind JS Node Save Button ──
    const jsSaveBtn = node.querySelector('.js-save-btn');
    if (jsSaveBtn) {
        jsSaveBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const payload = extractGraphJSON();
            try {
                const res = await fetch('/api/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.status === 'success') {
                    alert('JS Code saved successfully!');
                } else {
                    alert('Failed to save: ' + (data.message || 'unknown error'));
                }
            } catch (err) {
                alert('Error saving JS Code: ' + err.message);
            }
        });
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
    wrap3D(btn, '−');
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
function createNode(nodeType, canvasX, canvasY, forceId = null) {
    const template = document.querySelector(`#node-templates [data-type="${nodeType}"]`);
    if (!template) return null;

    const newNode = template.cloneNode(true);
    const newId = forceId || `node-${nodeIdCounter++}`;
    newNode.id = newId;

    newNode.querySelectorAll('.port').forEach(port => {
        port.dataset.node = newId;
    });

    newNode.style.left = `${canvasX}px`;
    newNode.style.top = `${canvasY}px`;

    canvasLayer.appendChild(newNode);
    bindNodeEvents(newNode);

    newNode.dataset.intendedX = canvasX;
    newNode.dataset.intendedY = canvasY;

    if (['LogicNode', 'ContextNode', 'RenderNode', 'CSSNode', 'JSNode', 'ClientJSNode'].includes(nodeType)) {
        initMonacoEditor(newNode, nodeType);
    }

    setTimeout(() => {
        if (newNode.parentNode) {
            const currentX = parseFloat(newNode.style.left);
            const currentY = parseFloat(newNode.style.top);
            if (Math.abs(currentX - canvasX) > 1 || Math.abs(currentY - canvasY) > 1) {
                newNode.style.left = `${canvasX}px`;
                newNode.style.top = `${canvasY}px`;
                updateAllWires();
            }
        }
    }, 500);

    return newNode;
}

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

    // Get mouse position relative to canvas container
    const rect = canvasContainer.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // Convert to canvas (unscaled) coordinates using current pan and scale
    const canvasX = (mouseX - panX) / scale;
    const canvasY = (mouseY - panY) / scale;

    createNode(nodeType, canvasX, canvasY);
});

function mountTextareaFallback(container, nodeElement, defaultValue) {
    container.innerHTML = '';
    const textarea = document.createElement('textarea');
    textarea.className = 'monaco-fallback-textarea';
    textarea.style.width = '100%';
    textarea.style.height = '100%';
    textarea.style.background = '#1e1e1e';
    textarea.style.color = '#d4d4d4';
    textarea.style.fontFamily = 'Consolas, Monaco, monospace';
    textarea.style.fontSize = '12px';
    textarea.style.border = 'none';
    textarea.style.resize = 'none';
    textarea.style.padding = '8px';
    textarea.value = defaultValue;
    container.appendChild(textarea);
    
    nodeElement._textareaFallback = textarea;
    
    // Polyfill the editor interface so existing methods don't crash
    nodeElement._monacoEditor = {
        getValue: () => textarea.value,
        setValue: (val) => { textarea.value = val; }
    };
}

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
    } else if (type === 'JSNode') {
        initConfig.value = `function process_logic(request) {
    // Write JavaScript logic here
    // e.g., request.context["result"] = "<h1>Hello from JS Node</h1>";
    return {};
}`;
        initConfig.language = 'javascript';
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
    } else if (type === 'ClientJSNode') {
        initConfig.value = `// Frontend JavaScript\nconsole.log("Hello from browser JS!");\n\nfunction onClick() {\n    alert("Button clicked!");\n}`;
        initConfig.language = 'javascript';
    }

    // --- NEW: Add Expand Button ---
    if (!nodeElement.querySelector('.monaco-expand-btn')) {
        const label = container.previousElementSibling;
        if (label && label.tagName === 'LABEL') {
            label.style.display = 'flex';
            label.style.justifyContent = 'space-between';
            label.style.alignItems = 'center';
            
            const btn = document.createElement('button');
            btn.className = 'node-btn monaco-expand-btn';
            wrap3D(btn, '⛶ Edit');
            btn.style.marginLeft = '10px';
            btn.style.padding = '2px 6px';
            
            
            btn.style.border = 'none';
            btn.onclick = (e) => {
                e.stopPropagation();
                openFullscreenEditor(nodeElement, initConfig.language);
            };
            label.appendChild(btn);
            
            // --- ADD SAVE FILE UI ---
            const saveContainer = document.createElement('div');
            saveContainer.className = 'node-file-save-container';
            saveContainer.style.display = 'flex';
            saveContainer.style.gap = '5px';
            saveContainer.style.marginBottom = '5px';
            saveContainer.style.marginTop = '5px';
            
            let defaultPlaceholder = 'filename';
            if (type === 'RenderNode') defaultPlaceholder = 'index.html';
            else if (type === 'CSSNode') defaultPlaceholder = 'styles.css';
            else if (type === 'JSNode') defaultPlaceholder = 'server_script.js';
            else if (type === 'ClientJSNode') defaultPlaceholder = 'script.js';
            else if (type === 'LogicNode' || type === 'ContextNode') defaultPlaceholder = 'logic.py';

            const fileInput = document.createElement('input');
            fileInput.type = 'text';
            fileInput.className = 'node-file-input nodrag';
            fileInput.placeholder = defaultPlaceholder;
            fileInput.style.flex = '1';
            fileInput.style.padding = '4px';
            fileInput.style.background = '#1e1e1e';
            fileInput.style.color = 'white';
            fileInput.style.border = '1px solid #555';
            fileInput.style.borderRadius = '3px';
            fileInput.style.fontSize = '12px';
            // Allow typing without dragging the node
            fileInput.onmousedown = (e) => e.stopPropagation();
            
            const saveBtn = document.createElement('button');
            wrap3D(saveBtn, 'Save');
            saveBtn.className = 'btn btn-secondary';
            saveBtn.style.padding = '4px 8px';
            saveBtn.style.fontSize = '12px';
            saveBtn.style.background = '#3b3b3b';
            saveBtn.style.color = '#fff';
            saveBtn.style.border = '1px solid #555';
            saveBtn.style.cursor = 'pointer';
            
            saveBtn.onclick = (e) => {
                e.stopPropagation();
                const filename = fileInput.value.trim() || defaultPlaceholder;
                let currentCode = '';
                if (nodeElement._monacoEditor) {
                    currentCode = nodeElement._monacoEditor.getValue();
                } else if (nodeElement._textareaFallback) {
                    currentCode = nodeElement._textareaFallback.value;
                }
                
                fetch('/api/node_file_save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        filename: filename,
                        content: currentCode,
                        node_type: type
                    })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert(`File saved successfully to ${data.path}`);
                    } else {
                        alert(`Error saving file: ${data.message}`);
                    }
                })
                .catch(err => alert("Save failed: " + err.message));
            };
            
            saveContainer.appendChild(fileInput);
            saveContainer.appendChild(saveBtn);
            
            // Insert between label and monaco container
            container.parentNode.insertBefore(saveContainer, container);
        }
    }

    // Set a safety timeout. If Monaco doesn't load in 2.5 seconds, mount fallback
    let fallbackTimeout = setTimeout(() => {
        if (!nodeElement._monacoEditor) {
            console.warn('[initMonacoEditor] Monaco loading timed out. Mounting textarea fallback.');
            mountTextareaFallback(container, nodeElement, initConfig.value);
        }
    }, 2500);

    if (window.require) {
        require(['vs/editor/editor.main'], function () {
            clearTimeout(fallbackTimeout);
            if (nodeElement._textareaFallback) {
                // Already fell back, ignore
                return;
            }
            const editor = monaco.editor.create(container, initConfig);
            nodeElement._monacoEditor = editor;

            const resizeObserver = new ResizeObserver(() => editor.layout());
            resizeObserver.observe(container);
        });
    } else {
        clearTimeout(fallbackTimeout);
        mountTextareaFallback(container, nodeElement, initConfig.value);
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
    timeout = 8000
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
                    'CSSNode',
                    'JSNode'
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
                console.warn('[waitForMonacoEditors] Timeout reached, resolving anyway.');
                resolve(); // resolve anyway
            }
        }, 50);
    });
}

/**
 * Robustly set Monaco editor value with retry.
 * If the editor isn't ready yet, keeps polling until it is.
 */
function _setMonacoValueWithRetry(nodeEl, value, lang, maxRetries = 30) {
    let attempts = 0;
    function trySet() {
        if (nodeEl._monacoEditor) {
            nodeEl._monacoEditor.setValue(value);
            // Auto-format after a short delay
            setTimeout(() => {
                try {
                    const action = nodeEl._monacoEditor.getAction('editor.action.formatDocument');
                    if (action) action.run();
                } catch (e) { /* formatting is best-effort */ }
            }, 400);
            return;
        }
        attempts++;
        if (attempts < maxRetries) {
            setTimeout(trySet, 200);
        } else {
            console.warn('[_setMonacoValueWithRetry] Editor never initialized for node:', nodeEl.id);
        }
    }
    trySet();
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
                'RenderNode',
                'CSSNode',
                'JSNode'].includes(
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

            // Store original config as fallback for extractGraphJSON
            nodeEl._loadedConfig = config;

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
                    nodeEl.querySelector('.filename-input').value = config.filename;
                if (config.html_code) {
                    _setMonacoValueWithRetry(nodeEl, config.html_code, 'html');
                }
                // Restore saved seed data
                if (config.seed) {
                    nodeEl.dataset.seed = JSON.stringify(config.seed);
                    // Show seed indicator on the node header
                    let spinner = nodeEl.querySelector('.seed-spinner');
                    if (!spinner) {
                        spinner = document.createElement('span');
                        spinner.className = 'seed-spinner';
                        const header = nodeEl.querySelector('.node-header');
                        if (header) header.appendChild(spinner);
                    }
                    spinner.innerHTML = ' 🌱 ✅';
                }
            } else if (type === 'LogicNode' || type === 'ContextNode' || type === 'JSNode') {
                if (config.code) {
                    const lang = type === 'JSNode' ? 'javascript' : 'python';
                    _setMonacoValueWithRetry(nodeEl, config.code, lang);
                }
            } else if (type === 'CSSNode') {
                if (config.css_filename)
                    nodeEl.querySelector('.css-filename-input').value = config.css_filename;
                if (config.css_code) {
                    _setMonacoValueWithRetry(nodeEl, config.css_code, 'css');
                }
            }
        });

        // Step 4: Draw connections
        // (guaranteed: nodes + editors ready)
        data.connections.forEach(conn => {
            const sourceId = conn.source || conn.from;
            const targetId = conn.target || conn.to;
            const sourceEl = document.getElementById(sourceId);
            const targetEl = document.getElementById(targetId);

            if (!sourceEl || !targetEl) {
                console.warn(
                    'Missing node for ' +
                    'connection:',
                    sourceId,
                    '->',
                    targetId
                );
                return;
            }

            const fromPort = sourceEl.querySelector('.out-port');
            const toPort = targetEl.querySelector('.in-port');

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

// --- Fullscreen Editor Logic ---
let fullscreenEditorInstance = null;
let currentEditingNode = null;

function openFullscreenEditor(nodeElement, language) {
    const modal = document.getElementById('fullscreen-editor-modal');
    if (!modal) return;
    
    currentEditingNode = nodeElement;
    
    // Get current value
    let currentValue = '';
    if (nodeElement._monacoEditor) {
        currentValue = nodeElement._monacoEditor.getValue();
    } else if (nodeElement._textareaFallback) {
        currentValue = nodeElement._textareaFallback.value;
    }
    
    modal.style.display = 'flex';
    
    const container = document.getElementById('fullscreen-monaco-container');
    if (!fullscreenEditorInstance && window.require) {
        require(['vs/editor/editor.main'], function () {
            fullscreenEditorInstance = monaco.editor.create(container, {
                value: currentValue,
                language: language || 'python',
                theme: 'vs-dark',
                minimap: { enabled: true },
                fontSize: 14,
                automaticLayout: true
            });
        });
    } else if (fullscreenEditorInstance) {
        // change language and value
        monaco.editor.setModelLanguage(fullscreenEditorInstance.getModel(), language || 'python');
        fullscreenEditorInstance.setValue(currentValue);
    } else {
        // Fallback for fullscreen if monaco failed globally
        container.innerHTML = '<textarea id="fullscreen-textarea" style="width:100%; height:100%; background:#1e1e1e; color:#d4d4d4; font-family:monospace; font-size:14px; padding:10px; border:none; resize:none;"></textarea>';
        document.getElementById('fullscreen-textarea').value = currentValue;
        document.getElementById('fullscreen-textarea').value = currentValue;
    }
    
    // Check if Seed button should be enabled
    const seedBtn = document.getElementById('btn-seed-generate');
    if (seedBtn) {
        seedBtn.disabled = true;
        seedBtn.dataset.seedPrompt = '';
        
        // Find parent Template Node
        const incomingWires = wires.filter(w => w.targetNode === nodeElement.id);
        for (const w of incomingWires) {
            const parent = document.getElementById(w.sourceNode);
            if (parent && (parent.dataset.type === 'RenderNode' || parent.dataset.type === 'TemplateNode')) {
                if (parent.dataset.seed) {
                    try {
                        const seed = JSON.parse(parent.dataset.seed);
                        const type = nodeElement.dataset.type;
                        if (type === 'CSSNode' && seed.css) {
                            seedBtn.disabled = false;
                            seedBtn.dataset.seedPrompt = seed.css;
                        } else if ((type === 'JSNode' || type === 'ClientJSNode') && seed.js) {
                            seedBtn.disabled = false;
                            seedBtn.dataset.seedPrompt = seed.js;
                        } else if (type === 'LogicNode' && seed.py) {
                            seedBtn.disabled = false;
                            seedBtn.dataset.seedPrompt = seed.py;
                        }
                    } catch(e){}
                }
            }
        }
    }
}

async function generateFromSeed() {
    const seedBtn = document.getElementById('btn-seed-generate');
    if (seedBtn && !seedBtn.disabled && seedBtn.dataset.seedPrompt) {
        const promptInput = document.getElementById('ai-prompt-input');
        if (promptInput) {
            promptInput.value = seedBtn.dataset.seedPrompt;
            toggleAIGeneration();
        }
    }
}

const fsSaveBtn = document.getElementById('fullscreen-save-btn');
const fsCloseBtn = document.getElementById('fullscreen-close-btn');

if (fsSaveBtn) {
    fsSaveBtn.addEventListener('click', () => {
        if (!currentEditingNode) return;
        
        let newValue = '';
        if (fullscreenEditorInstance) {
            newValue = fullscreenEditorInstance.getValue();
        } else {
            const ta = document.getElementById('fullscreen-textarea');
            if (ta) newValue = ta.value;
        }
        
        if (currentEditingNode._monacoEditor) {
            currentEditingNode._monacoEditor.setValue(newValue);
            // format
            setTimeout(() => {
                try {
                    const action = currentEditingNode._monacoEditor.getAction('editor.action.formatDocument');
                    if (action) action.run();
                } catch (e) {}
            }, 100);
        } else if (currentEditingNode._textareaFallback) {
            currentEditingNode._textareaFallback.value = newValue;
        }
        
        document.getElementById('fullscreen-editor-modal').style.display = 'none';
        currentEditingNode = null;
    });
}

if (fsCloseBtn) {
    fsCloseBtn.addEventListener('click', () => {
        document.getElementById('fullscreen-editor-modal').style.display = 'none';
        currentEditingNode = null;
    });
}

// --- Serialization & Backend API ---
function extractGraphJSON() {
    const nodes = [];
    document.querySelectorAll('#canvas-layer .node').forEach(nodeEl => {
        const id = nodeEl.id;
        const type = nodeEl.dataset.type;
        const x = parseFloat(nodeEl.style.left) || 0;
        const y = parseFloat(nodeEl.style.top) || 0;

        // _loadedConfig stores the original config from graph.json
        // so if Monaco hasn't loaded yet, we don't lose the AI-generated content
        const fallback = nodeEl._loadedConfig || {};

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
            } else {
                config.html_code = fallback.html_code || '';
            }
            // Persist seed data so it survives Save/Load
            if (nodeEl.dataset.seed) {
                try {
                    config.seed = JSON.parse(nodeEl.dataset.seed);
                } catch(e) {
                    config.seed = null;
                }
            }
        } else if (type === 'ModelNode') {
            config.query = nodeEl.querySelector('.query-input').value;
            config.paramsMap = nodeEl.querySelector('.params-input').value;
            config.contextKey = nodeEl.querySelector('.context-input').value;
            config.isWrite = nodeEl.querySelector('.is-write-input').checked;
        } else if (type === 'LogicNode' || type === 'ContextNode' || type === 'JSNode') {
            if (nodeEl._monacoEditor) {
                config.code = nodeEl._monacoEditor.getValue();
            } else {
                config.code = fallback.code || '';
            }
        } else if (type === 'CSSNode') {
            config.css_filename = nodeEl.querySelector('.css-filename-input').value;
            if (nodeEl._monacoEditor) {
                config.css_code = nodeEl._monacoEditor.getValue();
            } else {
                config.css_code = fallback.css_code || '';
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

function clearCanvas() {
    document.querySelectorAll('#canvas-layer .node').forEach(n => n.remove());
    document.querySelectorAll('#wire-layer .wire').forEach(w => w.remove());
    wires = [];
    nodeIdCounter = 10;
}

document.getElementById('btn-clear').addEventListener('click', clearCanvas);

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

let aiGenerationController = null;
let isAIGenerating = false;

async function toggleAIGeneration() {
    if (isAIGenerating) {
        if (aiGenerationController) {
            aiGenerationController.abort();
            aiGenerationController = null;
        }
        resetAIUIState();
        return;
    }
    await generateFullscreenCode();
}

function resetAIUIState() {
    isAIGenerating = false;
    const btn = document.getElementById('ai-generate-btn');
    const promptInput = document.getElementById('ai-prompt-input');
    const overlay = document.getElementById('ai-loading-overlay');
    const statusText = document.getElementById('ai-status-text');

    btn.innerHTML = '✨ Generate';
    btn.style.backgroundColor = '';
    btn.style.borderColor = '';
    
    promptInput.disabled = false;
    overlay.style.display = 'none';
    statusText.style.display = 'none';
}

function stripMarkdown(codeStr) {
    let clean = codeStr;
    if (clean.startsWith('```')) {
        const firstNewLine = clean.indexOf('\n');
        if (firstNewLine !== -1) {
            clean = clean.substring(firstNewLine + 1);
        }
    }
    if (clean.endsWith('```')) {
        clean = clean.substring(0, clean.length - 3);
    }
    return clean;
}

async function generateFullscreenCode() {
    const promptInput = document.getElementById('ai-prompt-input');
    const btn = document.getElementById('ai-generate-btn');
    const overlay = document.getElementById('ai-loading-overlay');
    const statusText = document.getElementById('ai-status-text');
    
    const prompt = promptInput.value.trim();
    if (!prompt) return;
    if (!currentEditingNode) return;

    isAIGenerating = true;
    aiGenerationController = new AbortController();
    
    // UI Updates
    btn.innerHTML = '⏸ Stop';
    btn.style.backgroundColor = '#ef4444';
    btn.style.borderColor = '#b91c1c';
    promptInput.disabled = true;
    overlay.style.display = 'flex';
    statusText.style.display = 'none';

    let currentCode = '';
    if (fullscreenEditorInstance) {
        currentCode = fullscreenEditorInstance.getValue();
    } else {
        const ta = document.getElementById('fullscreen-textarea');
        if (ta) currentCode = ta.value;
    }
    
    try {
        const response = await fetch('/api/ai/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: prompt,
                code: currentCode,
                node_type: currentEditingNode.dataset.type
            }),
            signal: aiGenerationController.signal
        });

        if (!response.ok) {
            const errText = await response.text();
            throw new Error(errText);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        let newCode = "";
        let firstChunkReceived = false;
        
        // Seed Parsing
        let isParsingSeed = false;
        let htmlCode = "";
        let seedCode = "";

        if (fullscreenEditorInstance) {
            fullscreenEditorInstance.setValue("");
        } else {
            const ta = document.getElementById('fullscreen-textarea');
            if (ta) ta.value = "";
        }

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            if (!firstChunkReceived) {
                firstChunkReceived = true;
                overlay.style.display = 'none';
                statusText.style.display = 'block';
            }

            const chunk = decoder.decode(value, { stream: true });
            newCode += chunk;
            
            const separator = '---SEED_SEPARATOR---';
            if ((currentEditingNode.dataset.type === 'RenderNode' || currentEditingNode.dataset.type === 'TemplateNode') && newCode.includes(separator)) {
                const parts = newCode.split(separator);
                htmlCode = parts[0];
                seedCode = parts.slice(1).join(separator);
                isParsingSeed = true;
            } else {
                htmlCode = newCode;
            }
            
            const cleanCode = stripMarkdown(htmlCode);

            if (fullscreenEditorInstance) {
                fullscreenEditorInstance.setValue(cleanCode);
            } else {
                const ta = document.getElementById('fullscreen-textarea');
                if (ta) ta.value = cleanCode;
            }
            
            if (isParsingSeed) {
                statusText.innerText = "Generating Seed...";
                let spinner = currentEditingNode.querySelector('.seed-spinner');
                if (!spinner) {
                    spinner = document.createElement('span');
                    spinner.className = 'seed-spinner';
                    spinner.innerHTML = ' 🌱 <span style="font-size:10px;animation:spin 1s linear infinite;display:inline-block;">⚙️</span>';
                    const header = currentEditingNode.querySelector('.node-header');
                    if (header) header.appendChild(spinner);
                }
            }
        }
        
        if (isParsingSeed && seedCode) {
            try {
                let cleanSeed = stripMarkdown(seedCode.trim());
                let startIndex = cleanSeed.indexOf('{');
                let endIndex = cleanSeed.lastIndexOf('}');
                if (startIndex !== -1 && endIndex !== -1 && endIndex >= startIndex) {
                    const jsonStr = cleanSeed.substring(startIndex, endIndex + 1);
                    const seedObj = JSON.parse(jsonStr);
                    currentEditingNode.dataset.seed = JSON.stringify(seedObj);
                    console.log("Saved Node Seed:", seedObj);
                    
                    const spinner = currentEditingNode.querySelector('.seed-spinner');
                    if (spinner) spinner.innerHTML = ' 🌱 ✅';
                } else {
                    throw new Error("No JSON object found in seed.");
                }
            } catch(e) {
                console.error("Failed to parse seed:", e, seedCode);
                const spinner = currentEditingNode.querySelector('.seed-spinner');
                if (spinner) spinner.innerHTML = ' 🌱 ❌';
            }
        }
        
        if (fullscreenEditorInstance) {
            setTimeout(() => {
                try {
                    const action = fullscreenEditorInstance.getAction('editor.action.formatDocument');
                    if (action) action.run();
                } catch (e) {}
            }, 100);
        }

        promptInput.value = '';

    } catch (err) {
        if (err.name === 'AbortError') {
            console.log('AI Generation Aborted');
        } else {
            alert("Generation Error: " + err.message);
        }
    } finally {
        resetAIUIState();
    }
}

// --- AI PROVIDER SETTINGS CONTROLLER ---
function toggleProviderFields() {
    const selectedProvider = document.getElementById('provider-select').value;
    document.querySelectorAll('.provider-fields-group').forEach(group => {
        if (group.dataset.provider === selectedProvider) {
            group.style.display = 'block';
        } else {
            group.style.display = 'none';
        }
    });
}

function openSettings() {
    fetch('/api/settings/load')
        .then(res => res.json())
        .then(data => {
            document.getElementById('provider-select').value = data.SELECTED_AI_PROVIDER || 'ollama';
            
            document.getElementById('endpoint-ollama').value = data.OLLAMA_API_ENDPOINT || 'http://localhost:11434/api/generate';
            document.getElementById('model-ollama').value = data.OLLAMA_MODEL || 'gemma4:26b';

            document.getElementById('key-gemini').value = data.GEMINI_API_KEY || '';
            document.getElementById('model-gemini').value = data.GEMINI_MODEL || 'gemini-1.5-flash';

            document.getElementById('key-gpt').value = data.OPENAI_API_KEY || '';
            document.getElementById('model-gpt').value = data.OPENAI_MODEL || 'gpt-4o-mini';

            document.getElementById('key-claude').value = data.CLAUDE_API_KEY || '';
            document.getElementById('model-claude').value = data.CLAUDE_MODEL || 'claude-3-5-sonnet-20241022';

            document.getElementById('key-deepseek').value = data.DEEPSEEK_API_KEY || '';
            document.getElementById('model-deepseek').value = data.DEEPSEEK_MODEL || 'deepseek-chat';

            document.getElementById('key-openrouter').value = data.OPENROUTER_API_KEY || '';
            document.getElementById('model-openrouter').value = data.OPENROUTER_MODEL || 'google/gemini-2.0-flash-exp:free';

            document.getElementById('key-nvidia').value = data.NVIDIA_API_KEY || '';
            document.getElementById('model-nvidia').value = data.NVIDIA_MODEL || 'qwen/qwen3-coder-480b-a35b-instruct';

            document.getElementById('key-glm').value = data.GLM_API_KEY || '';
            document.getElementById('model-glm').value = data.GLM_MODEL || 'glm-4-flash';

            document.getElementById('key-dough').value = data.DOUGH_API_KEY || '';
            document.getElementById('model-dough').value = data.DOUGH_MODEL || 'deepseek-chat';

            document.getElementById('key-custom').value = data.CUSTOM_API_KEY || '';
            document.getElementById('model-custom').value = data.CUSTOM_MODEL || 'custom-model';
            document.getElementById('endpoint-custom').value = data.CUSTOM_API_ENDPOINT || '';

            toggleProviderFields();
            document.getElementById('settings-modal').style.display = 'flex';
        })
        .catch(err => {
            alert('Failed to load settings: ' + err.message);
        });
}

function closeSettings() {
    document.getElementById('settings-modal').style.display = 'none';
}

function saveSettings() {
    const payload = {
        SELECTED_AI_PROVIDER: document.getElementById('provider-select').value,

        OLLAMA_API_ENDPOINT: document.getElementById('endpoint-ollama').value.trim(),
        OLLAMA_MODEL: document.getElementById('model-ollama').value.trim() || 'gemma4:26b',

        GEMINI_API_KEY: document.getElementById('key-gemini').value.trim(),
        GEMINI_MODEL: document.getElementById('model-gemini').value.trim() || 'gemini-1.5-flash',

        OPENAI_API_KEY: document.getElementById('key-gpt').value.trim(),
        OPENAI_MODEL: document.getElementById('model-gpt').value.trim() || 'gpt-4o-mini',

        CLAUDE_API_KEY: document.getElementById('key-claude').value.trim(),
        CLAUDE_MODEL: document.getElementById('model-claude').value.trim() || 'claude-3-5-sonnet-20241022',

        DEEPSEEK_API_KEY: document.getElementById('key-deepseek').value.trim(),
        DEEPSEEK_MODEL: document.getElementById('model-deepseek').value.trim() || 'deepseek-chat',

        OPENROUTER_API_KEY: document.getElementById('key-openrouter').value.trim(),
        OPENROUTER_MODEL: document.getElementById('model-openrouter').value.trim() || 'google/gemini-2.0-flash-exp:free',

        NVIDIA_API_KEY: document.getElementById('key-nvidia').value.trim(),
        NVIDIA_MODEL: document.getElementById('model-nvidia').value.trim() || 'qwen/qwen3-coder-480b-a35b-instruct',

        GLM_API_KEY: document.getElementById('key-glm').value.trim(),
        GLM_MODEL: document.getElementById('model-glm').value.trim() || 'glm-4-flash',

        DOUGH_API_KEY: document.getElementById('key-dough').value.trim(),
        DOUGH_MODEL: document.getElementById('model-dough').value.trim() || 'deepseek-chat',

        CUSTOM_API_KEY: document.getElementById('key-custom').value.trim(),
        CUSTOM_MODEL: document.getElementById('model-custom').value.trim() || 'custom-model',
        CUSTOM_API_ENDPOINT: document.getElementById('endpoint-custom').value.trim()
    };

    fetch('/api/settings/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Settings saved successfully!');
            closeSettings();
        } else {
            alert('Failed to save settings: ' + (data.message || 'unknown error'));
        }
    })
    .catch(err => {
        alert('Error saving settings: ' + err.message);
    });
}

// --- API CONNECTION TEST LOGIC ---
let apiTestController = null;

async function testAPIConnection() {
    const promptInput = document.getElementById('api-test-prompt');
    const outputArea = document.getElementById('api-test-output');
    const testBtn = document.querySelector('button[onclick="testAPIConnection()"]');
    
    // First, save settings before testing so the backend has the latest keys
    // It's a quick invisible save logic or we can just rely on user having clicked "Save Config"
    // Actually, let's just warn them or test what's saved.
    
    let prompt = promptInput.value.trim() || 'Say hello';
    
    if (apiTestController) {
        apiTestController.abort();
        apiTestController = null;
    }

    apiTestController = new AbortController();
    outputArea.value = '';
    testBtn.innerHTML = 'Testing...';
    testBtn.disabled = true;

    try {
        const response = await fetch('/api/ai/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: prompt,
                code: '',
                node_type: 'Test'
            }),
            signal: apiTestController.signal
        });

        if (!response.ok) {
            const errText = await response.text();
            throw new Error(errText);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            outputArea.value += chunk;
            outputArea.scrollTop = outputArea.scrollHeight;
        }
        
    } catch (err) {
        if (err.name === 'AbortError') {
            console.log('Test Aborted');
        } else {
            outputArea.value = "Error: " + err.message;
        }
    } finally {
        testBtn.innerHTML = '🔌 Test API';
        testBtn.disabled = false;
        apiTestController = null;
    }
}

// --- MASTER ARCHITECT ENGINE ---
async function runMasterArchitect() {
    const promptInput = document.getElementById('master-architect-prompt');
    const prompt = promptInput.value.trim();
    if (!prompt) return;

    const btn = document.getElementById('btn-master-architect');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span>⏳</span> Thinking...';
    btn.disabled = true;

    try {
        const response = await fetch('/api/ai/architect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: prompt })
        });
        
        if (!response.ok) {
            const errText = await response.text();
            throw new Error(errText);
        }

        const data = await response.json();
        if (data.status === 'error') {
            throw new Error(data.message);
        }

        // Clear canvas
        clearCanvas();
        
        // Render graph (reusing load logic but manually simulating it)
        const nodesData = data.graph.nodes || [];
        const connsData = data.graph.connections || [];
        
        nodesData.forEach(n => {
            const nodeEl = createNode(n.type, n.x, n.y, n.id);
            if (n.config) {
                // Wait for monaco
                setTimeout(() => {
                    if (n.config.code && nodeEl._monacoEditor) {
                        nodeEl._monacoEditor.setValue(n.config.code);
                    } else if (n.config.html_code && nodeEl._monacoEditor) {
                        nodeEl._monacoEditor.setValue(n.config.html_code);
                    } else if (n.config.css_code && nodeEl._monacoEditor) {
                        nodeEl._monacoEditor.setValue(n.config.css_code);
                    }
                    if (n.config.filename) {
                        const fileInput = nodeEl.querySelector('.node-file-input');
                        if (fileInput) fileInput.value = n.config.filename;
                    }
                }, 500);
            }
        });

        // Store context instructions on nodes BEFORE adding connections
        setTimeout(() => {
            if (data.instructions) {
                for (const [nodeId, instruction] of Object.entries(data.instructions)) {
                    const el = document.getElementById(nodeId);
                    if (el) {
                        el.dataset.aiInstruction = instruction;
                    }
                }
            }
        }, 50);

        // Auto-trigger TemplateNode explicitly since it might not be a target of a connection
        setTimeout(() => {
            const templateNodes = document.querySelectorAll('.node[data-type="RenderNode"], .node[data-type="TemplateNode"]');
            templateNodes.forEach(node => {
                if (node.dataset.aiInstruction) {
                    const instruction = node.dataset.aiInstruction || `Generate HTML for: ${prompt}`;
                    node.dataset.aiInstruction = ''; // clear
                    enqueueAIGeneration(node, instruction);
                }
            });
        }, 100);

        // Add connections (which will now trigger the interceptor because instructions are already set)
        // These will be appended to the AI Generation Queue AFTER the Template Node
        setTimeout(() => {
            connsData.forEach(c => {
                const sourceNode = document.getElementById(c.source);
                const targetNode = document.getElementById(c.target);
                if (sourceNode && targetNode) {
                    const sourcePort = sourceNode.querySelector('.port-out');
                    const targetPort = targetNode.querySelector('.port-in');
                    if (sourcePort && targetPort) {
                        createWire(sourcePort, targetPort);
                    }
                }
            });
        }, 200);

    } catch (err) {
        alert('Architecture Generation Error: ' + err.message);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

let aiGenerationQueue = [];
let isQueueGenerating = false;

function enqueueAIGeneration(nodeElement, instruction) {
    aiGenerationQueue.push({ node: nodeElement, instruction: instruction });
    processAIGenerationQueue();
}

function processAIGenerationQueue() {
    if (isQueueGenerating || aiGenerationQueue.length === 0) return;
    
    isQueueGenerating = true;
    const task = aiGenerationQueue.shift();
    
    // Auto trigger
    autoTriggerNodeAI(task.node, task.instruction);
    
    // Poll the Generate button to know when it finishes
    const checkInterval = setInterval(() => {
        const btn = document.getElementById('btn-ai-generate');
        // The button text changes to "Generating..." while it works
        if (btn && btn.innerText.includes('✨ Generate') && !btn.disabled) {
            clearInterval(checkInterval);
            
            // Wait a tiny bit then close
            setTimeout(() => {
                closeFullscreenEditor();
                
                // Wait another tiny bit before doing the next one
                setTimeout(() => {
                    isQueueGenerating = false;
                    processAIGenerationQueue();
                }, 500);
            }, 1000);
        }
    }, 1000);
}

function autoTriggerNodeAI(nodeElement, instruction) {
    // Open the editor
    const lang = nodeElement.dataset.type === 'CSSNode' ? 'css' : 
                 nodeElement.dataset.type === 'ClientJSNode' || nodeElement.dataset.type === 'JSNode' ? 'javascript' : 
                 nodeElement.dataset.type === 'RenderNode' ? 'html' : 'python';
                 
    openFullscreenEditor(nodeElement, lang);
    
    // Set prompt and trigger generate
    setTimeout(() => {
        const promptInput = document.getElementById('ai-prompt-input');
        const genBtn = document.getElementById('btn-ai-generate');
        if (promptInput && genBtn) {
            promptInput.value = instruction;
            genBtn.click();
            // Optional: Temporarily disable button to ensure our polling sees it start
            genBtn.disabled = true; 
            setTimeout(() => { genBtn.disabled = false; }, 500);
        }
    }, 500);
}

// Intercept wire connection to trigger chain reaction
const _originalCreateWire = createWire;
createWire = function(fromPort, toPort) {
    _originalCreateWire(fromPort, toPort);
    
    // Auto-trigger AI if target node has a pending instruction
    if (toPort && toPort.dataset && toPort.dataset.node) {
        const toNode = document.getElementById(toPort.dataset.node);
        if (toNode && toNode.dataset.aiInstruction) {
            const instruction = toNode.dataset.aiInstruction;
            // Check if editor is empty or mostly empty
            let currentCode = '';
            if (toNode._monacoEditor) currentCode = toNode._monacoEditor.getValue();
            
            if (currentCode.trim().length < 50 || currentCode.includes('Write Python logic here') || currentCode.includes('CSS styles for your page') || currentCode.includes('Frontend JavaScript')) {
                console.log("Auto-triggering AI for", toNode.id, "with instruction:", instruction);
                // clear it so it doesn't fire again
                toNode.dataset.aiInstruction = '';
                
                enqueueAIGeneration(toNode, instruction);
            }
        }
    }
};

async function resetDatabase() {
    if (!confirm('Are you sure you want to drop and reset the entire database? All records will be lost!')) return;
    try {
        const res = await fetch('/api/db/reset', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            alert('Database successfully reset!');
        } else {
            alert('Failed to reset database: ' + (data.message || 'Unknown error'));
        }
    } catch(e) {
        alert('Error communicating with server: ' + e);
    }
}
