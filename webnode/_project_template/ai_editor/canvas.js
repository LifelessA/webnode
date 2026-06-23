// --- STATE ---
let panX = 0, panY = 0, scale = 1;
let isPanning = false, startX, startY;
let activeNode = null;
let isWiring = false;
let startPort = null;
let wires = [];
let nodeIdCounter = 10; // Reserve < 10 for defaults
let loadedGraphHash = null;
let waitingForAnswer = false;


const canvasLayer = document.getElementById('canvas-layer');
const canvasContainer = document.getElementById('canvas-container');
const wireLayer = document.getElementById('wire-layer');
const iframe = document.getElementById('preview-iframe');
const addressInput = document.getElementById('address-input');

// --- INITIALIZATION ---
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

    // Drag-over/Drop handler for palette drag and drop
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

        if (['LogicNode', 'ContextNode', 'RenderNode', 'CSSNode', 'JSNode'].includes(nodeType)) {
            initMonacoEditor(newNode, nodeType);
        }

        // Safety: after a short delay, reapply position if it changed
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
    });

    // Load graph automatically
    loadGraphJSON();

    // Load AI settings to update active model display
    fetch('/api/settings/load')
        .then(res => res.json())
        .then(data => updateActiveModelDisplay(data))
        .catch(() => {});
}

// --- PANNING & ZOOMING ---
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
    if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        const zoomIntensity = 0.05;
        const delta = e.deltaY > 0 ? -1 : 1;
        let newScale = scale * Math.exp(delta * zoomIntensity);
        newScale = Math.min(Math.max(0.2, newScale), 3);
        if (newScale === scale) return;

        const rect = canvasContainer.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        const canvasX = (mouseX - panX) / scale;
        const canvasY = (mouseY - panY) / scale;

        scale = newScale;
        panX = mouseX - canvasX * scale;
        panY = mouseY - canvasY * scale;

        updateCanvasTransform();
    }
});

function updateCanvasTransform() {
    canvasLayer.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
    canvasContainer.style.backgroundPosition = `${panX}px ${panY}px`;
    canvasContainer.style.backgroundSize = `${20 * scale}px ${20 * scale}px`;
    updateAllWires();
}

// --- DYNAMIC NODE EVENT BINDING ---
function bindNodeEvents(node) {
    const header = node.querySelector('.node-header');
    if (header) {
        header.addEventListener('mousedown', startNodeDrag);
    }

    node.querySelectorAll('.port').forEach(port => {
        port.addEventListener('mousedown', onPortMouseDown);
        port.addEventListener('mouseup', onPortMouseUp);
    });

    // Inject delete button
    if (!node.querySelector('.node-delete-btn')) {
        const btn = document.createElement('button');
        btn.className = 'node-delete-btn';
        btn.title = 'Delete node';
        btn.textContent = '✕';
        btn.addEventListener('mousedown', e => e.stopPropagation());
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteNode(node.id);
        });
        node.appendChild(btn);
    }

    // Bind JS Node Save button
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

// --- DELETION HANDLERS ---
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

// Clean delete wire
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

function deleteWireByPath(pathEl) {
    const wireObj = wires.find(w => w.path === pathEl);
    deleteWire(wireObj);
}

// --- WIRE HOVER DISCONNECT BUTTON ---
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
    btn.addEventListener('mouseenter', () => { btn.style.display = 'flex'; });
    btn.addEventListener('mouseleave', () => { btn.style.display = 'none'; _hoveredWire = null; });
    canvasContainer.appendChild(btn);
}

function _getBezierMidpoint(x1, y1, x2, y2) {
    const curvature = Math.abs(x2 - x1) * 0.5;
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

        const start = getPortCoords(wireObj.fromEl);
        const end = getPortCoords(wireObj.toEl);
        const mid = _getBezierMidpoint(start.x, start.y, end.x, end.y);

        btn.style.left = `${mid.x}px`;
        btn.style.top = `${mid.y}px`;
        btn.style.display = 'flex';
    });

    path.addEventListener('mouseleave', (e) => {
        const btn = document.getElementById('wire-disconnect-btn');
        if (btn && e.relatedTarget === btn) return;
        if (btn) btn.style.display = 'none';
        _hoveredWire = null;
    });
}

// --- MONACO EDITOR ---
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
        initConfig.value = `def process_logic(request):\n    return {}`;
    } else if (type === 'JSNode') {
        initConfig.value = `function process_logic(request) {\n    return {};\n}`;
        initConfig.language = 'javascript';
    } else if (type === 'ContextNode') {
        initConfig.value = `def node_logic(request):\n    return {}`;
    } else if (type === 'RenderNode') {
        initConfig.value = `<h1>Template</h1>`;
        initConfig.language = 'html';
    } else if (type === 'CSSNode') {
        initConfig.value = `body { }`;
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

// --- NODE DRAGGING ---
function startNodeDrag(e) {
    if (e.target.classList.contains('port') ||
        e.target.classList.contains('in-port') ||
        e.target.classList.contains('out-port')) return;

    const node = e.target.closest('.node');
    if (!node) return;
    activeNode = node;
    
    let maxZ = 10;
    document.querySelectorAll('#canvas-layer .node').forEach(n => {
        let z = parseInt(n.style.zIndex || 10);
        if (z > maxZ) maxZ = z;
    });
    activeNode.style.zIndex = maxZ + 1;

    const startNodeX = parseFloat(activeNode.style.left) || 0;
    const startNodeY = parseFloat(activeNode.style.top) || 0;
    const startMouseX = e.clientX;
    const startMouseY = e.clientY;

    function onMouseMove(moveEvent) {
        const dx = (moveEvent.clientX - startMouseX) / scale;
        const dy = (moveEvent.clientY - startMouseY) / scale;
        activeNode.style.left = `${startNodeX + dx}px`;
        activeNode.style.top = `${startNodeY + dy}px`;
        
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

// --- WIRING (SVGs) ---
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

// Cancel dragging connection
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
    bindWireHover(wireObj);

    // Style active/error wires based on live state
    if (serverIsLive) {
        if (window.activeWires && window.activeWires.has(wireObj)) {
            path.classList.add('active');
        } else {
            path.classList.add('error');
        }
    } else {
        path.classList.add('error');
    }

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
    if (!pathEl) return;
    const curvature = Math.abs(x2 - x1) * 0.5;
    const d = `M ${x1} ${y1} C ${x1 + curvature} ${y1}, ${x2 - curvature} ${y2}, ${x2} ${y2}`;
    pathEl.setAttribute('d', d);
}

// --- MONACO EDIT RETRY ---
function _setMonacoValueWithRetry(nodeEl, value, lang, maxRetries = 30) {
    let attempts = 0;
    function trySet() {
        if (nodeEl._monacoEditor) {
            nodeEl._monacoEditor.setValue(value);
            setTimeout(() => {
                try {
                    const action = nodeEl._monacoEditor.getAction('editor.action.formatDocument');
                    if (action) action.run();
                } catch (e) {}
            }, 400);
            return;
        }
        attempts++;
        if (attempts < maxRetries) {
            setTimeout(trySet, 200);
        }
    }
    trySet();
}

function waitForMonacoEditors(timeout = 8000) {
    return new Promise(resolve => {
        const start = Date.now();
        const check = setInterval(() => {
            const pending = document.querySelectorAll('.monaco-container');
            const allReady = Array.from(pending).every(el => {
                const node = el.closest('.node');
                if (!node) return true;
                const type = node.dataset.type;
                const needsEditor = ['LogicNode', 'ContextNode', 'RenderNode', 'CSSNode', 'JSNode'].includes(type);
                return !needsEditor || !!node._monacoEditor;
            });

            if (allReady) {
                clearInterval(check);
                resolve();
                return;
            }

            if (Date.now() - start > timeout) {
                clearInterval(check);
                resolve();
            }
        }, 50);
    });
}

// --- LOAD GRAPH JSON ---
async function loadGraphJSON() {
    try {
        const res = await fetch('/api/load');
        const data = await res.json();

        if (!data?.nodes?.length) return;

        // Clear canvas
        document.querySelectorAll('#canvas-layer .node').forEach(n => n.remove());
        document.querySelectorAll('#wire-layer .wire').forEach(w => w.remove());
        wires = [];

        let maxId = 10;

        // Create nodes
        data.nodes.forEach(nodeData => {
            const template = document.querySelector(`#node-templates [data-type="${nodeData.type}"]`);
            if (!template) return;

            const newNode = template.cloneNode(true);
            newNode.id = nodeData.id;

            const nId = parseInt(nodeData.id.replace('node-', ''));
            if (!isNaN(nId) && nId > maxId) maxId = nId;

            newNode.querySelectorAll('.port').forEach(port => {
                port.dataset.node = nodeData.id;
            });

            newNode.style.left = `${nodeData.x}px`;
            newNode.style.top = `${nodeData.y}px`;

            canvasLayer.appendChild(newNode);
            bindNodeEvents(newNode);

            if (['LogicNode', 'ContextNode', 'RenderNode', 'CSSNode', 'JSNode'].includes(nodeData.type)) {
                initMonacoEditor(newNode, nodeData.type);
            }
        });

        nodeIdCounter = maxId + 1;

        await waitForMonacoEditors();

        // Load config values
        data.nodes.forEach(nodeData => {
            const nodeEl = document.getElementById(nodeData.id);
            if (!nodeEl) return;

            const config = nodeData.config || {};
            const type = nodeData.type;
            nodeEl._loadedConfig = config;

            if (type === 'ServerNode') {
                const ipEl = nodeEl.querySelector('.ip-input');
                const portEl = nodeEl.querySelector('.port-input');
                if (ipEl && config.ip) ipEl.value = config.ip;
                if (portEl && config.port) portEl.value = config.port;
            } else if (type === 'URLNode') {
                const pathEl = nodeEl.querySelector('.path-input');
                if (pathEl && config.path) pathEl.value = config.path;
            } else if (type === 'ModelNode') {
                const queryEl = nodeEl.querySelector('.query-input');
                const paramsEl = nodeEl.querySelector('.params-input');
                const contextEl = nodeEl.querySelector('.context-input');
                const isWriteEl = nodeEl.querySelector('.is-write-input');
                if (queryEl && config.query) queryEl.value = config.query;
                if (paramsEl && config.paramsMap) paramsEl.value = config.paramsMap;
                if (contextEl && config.contextKey) contextEl.value = config.contextKey;
                if (isWriteEl && config.isWrite !== undefined) isWriteEl.checked = config.isWrite;
            } else if (type === 'RenderNode') {
                const filenameEl = nodeEl.querySelector('.filename-input');
                if (filenameEl && config.filename) filenameEl.value = config.filename;
                if (config.html_code) {
                    _setMonacoValueWithRetry(nodeEl, config.html_code, 'html');
                }
            } else if (type === 'LogicNode' || type === 'ContextNode' || type === 'JSNode') {
                if (config.code) {
                    const lang = type === 'JSNode' ? 'javascript' : 'python';
                    _setMonacoValueWithRetry(nodeEl, config.code, lang);
                }
            } else if (type === 'CSSNode') {
                const cssFilenameEl = nodeEl.querySelector('.css-filename-input');
                if (cssFilenameEl && config.css_filename) cssFilenameEl.value = config.css_filename;
                if (config.css_code) {
                    _setMonacoValueWithRetry(nodeEl, config.css_code, 'css');
                }
            }
        });

        // Draw connections
        data.connections.forEach(conn => {
            const sourceId = conn.source || conn.from;
            const targetId = conn.target || conn.to;
            const sourceEl = document.getElementById(sourceId);
            const targetEl = document.getElementById(targetId);
            if (!sourceEl || !targetEl) return;

            const fromPort = sourceEl.querySelector('.out-port');
            const toPort = targetEl.querySelector('.in-port');
            if (fromPort && toPort) {
                createWire(fromPort, toPort);
            }
        });

        updateAllWires();

        // Sync the loaded hash to avoid redundant reloads
        try {
            const statusRes = await fetch('/api/status');
            const statusData = await statusRes.json();
            if (statusData.graph_hash) {
                loadedGraphHash = statusData.graph_hash;
            }
        } catch (e) {}

        return data;

    } catch (e) {
        console.error('Failed to load graph:', e);
    }
}

// --- SERIALIZATION ---
function extractGraphJSON() {
    const nodes = [];
    document.querySelectorAll('#canvas-layer .node').forEach(nodeEl => {
        const id = nodeEl.id;
        const type = nodeEl.dataset.type;
        const x = parseFloat(nodeEl.style.left) || 0;
        const y = parseFloat(nodeEl.style.top) || 0;
        const fallback = nodeEl._loadedConfig || {};

        let config = {};
        if (type === 'ServerNode') {
            const ipEl = nodeEl.querySelector('.ip-input');
            const portEl = nodeEl.querySelector('.port-input');
            config.ip = ipEl ? ipEl.value : (fallback.ip || '127.0.0.1');
            config.port = portEl ? parseInt(portEl.value, 10) : (fallback.port || 8000);
        } else if (type === 'URLNode') {
            const pathEl = nodeEl.querySelector('.path-input');
            config.path = pathEl ? pathEl.value : (fallback.path || '/');
        } else if (type === 'RenderNode') {
            const filenameEl = nodeEl.querySelector('.filename-input');
            config.filename = filenameEl ? filenameEl.value : (fallback.filename || 'index.html');
            if (nodeEl._monacoEditor) {
                config.html_code = nodeEl._monacoEditor.getValue();
            } else {
                config.html_code = fallback.html_code || '';
            }
        } else if (type === 'ModelNode') {
            const queryEl = nodeEl.querySelector('.query-input');
            const paramsEl = nodeEl.querySelector('.params-input');
            const contextEl = nodeEl.querySelector('.context-input');
            const isWriteEl = nodeEl.querySelector('.is-write-input');
            config.query = queryEl ? queryEl.value : (fallback.query || '');
            config.paramsMap = paramsEl ? paramsEl.value : (fallback.paramsMap || '');
            config.contextKey = contextEl ? contextEl.value : (fallback.contextKey || '');
            config.isWrite = isWriteEl ? isWriteEl.checked : (fallback.isWrite || false);
        } else if (type === 'LogicNode' || type === 'ContextNode' || type === 'JSNode') {
            if (nodeEl._monacoEditor) {
                config.code = nodeEl._monacoEditor.getValue();
            } else {
                config.code = fallback.code || '';
            }
        } else if (type === 'CSSNode') {
            const cssFilenameEl = nodeEl.querySelector('.css-filename-input');
            config.css_filename = cssFilenameEl ? cssFilenameEl.value : (fallback.css_filename || 'style.css');
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

function resetCanvas() {
    document.querySelectorAll('#canvas-layer .node').forEach(n => n.remove());
    document.querySelectorAll('#wire-layer .wire').forEach(w => w.remove());
    wires = [];
    nodeIdCounter = 10;
}

// --- DEFENSIVE TOOLBAR BINDINGS ---
const btnSave = document.getElementById('btn-save');
if (btnSave) {
    btnSave.addEventListener('click', async () => {
        const payload = extractGraphJSON();
        try {
            await fetch('/api/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            alert('Graph JSON saved locally!');
        } catch (e) {
            alert('Failed to save.');
        }
    });
}

const btnDeploy = document.getElementById('btn-deploy');
if (btnDeploy) {
    btnDeploy.addEventListener('click', async () => {
        const payload = extractGraphJSON();
        try {
            const res = await fetch('/api/deploy', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await res.json();
            if (result.status === 'success') {
                alert('Deployed successfully!');
            } else {
                alert('Failed to deploy: ' + result.message);
            }
        } catch (e) {
            alert('Cannot connect to backend compiler.');
        }
    });
}

const btnStop = document.getElementById('btn-stop');
if (btnStop) {
    btnStop.addEventListener('click', async () => {
        try {
            await fetch('/api/stop', { method: 'POST' });
        } catch (e) {}
    });
}

const btnClear = document.getElementById('btn-clear');
if (btnClear) {
    btnClear.addEventListener('click', resetCanvas);
}

// --- PREVIEW CONTROLLERS ---
function reloadPreview() {
    if (iframe) iframe.src = iframe.src;
}

function goHome() {
    if (iframe) iframe.src = "http://localhost:8000/";
}

// --- POLLING & FLOW TRAVERSAL ---
let serverIsLive = false;
let errorState = {};

async function pollServerStatus() {
    try {
        const [statusRes, errorsRes] = await Promise.all([
            fetch('/api/status'),
            fetch('/api/errors').catch(() => null)
        ]);

        const data = await statusRes.json();
        errorState = errorsRes ? await errorsRes.json().catch(() => ({})) : {};
        serverIsLive = (data.status === 'live');

        if (data.graph_hash) {
            const isGenerating = (statusIndicator && statusIndicator.classList.contains('generating')) || window.isHealingRuntime;
            if (loadedGraphHash && loadedGraphHash !== data.graph_hash && !isGenerating) {
                console.log("Canvas out of sync, reloading graph from backend...");
                loadGraphJSON();
            }
            loadedGraphHash = data.graph_hash;
        }
    } catch (e) {
        serverIsLive = false;
        errorState = {};
    }


    updateVisualFlow();
    updateNodeErrors();

    // Trigger runtime self-healing if a new error is detected
    if (errorState && Object.keys(errorState).length > 0 && !window.isHealingRuntime) {
        const errKeys = Object.keys(errorState);
        const err = errorState[errKeys[0]];
        const errString = `${err.node_type}: ${err.error_type} - ${err.message}`;

        if (window.lastHealedError !== errString) {
            window.isHealingRuntime = true;
            window.lastHealedError = errString;
            
            // Clear backend error state to prevent infinite loops
            fetch('/api/errors/clear', { method: 'POST' }).catch(() => {});
            
            triggerRuntimeHeal(err);
        }
    }
}

async function triggerRuntimeHeal(err) {
    const errorMsg = `Runtime Error in Node "${err.node_type}" (${err.error_type}): ${err.message}`;

    const systemMsg = document.createElement('div');
    systemMsg.className = 'message user';
    systemMsg.style.background = 'rgba(239, 68, 68, 0.15)';
    systemMsg.style.border = '1px solid rgba(239, 68, 68, 0.4)';
    systemMsg.style.color = '#f87171';
    systemMsg.innerHTML = `🚨 <b>[Runtime Self-Healing]</b> App error detected during usage:<br><code>${errorMsg}</code><br>AI is automatically resolving this bug...`;
    if (chatHistory) {
        chatHistory.appendChild(systemMsg);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    if (statusIndicator) statusIndicator.className = 'status-dot generating';
    if (statusText) statusText.innerText = 'AI Healing Runtime...';

    const aiMsg = document.createElement('div');
    aiMsg.className = 'message ai';
    aiMsg.innerHTML = 'Debugging logic code and patching graph...';
    if (chatHistory) {
        chatHistory.appendChild(aiMsg);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    let streamText = "";
    let parsedNodeIds = new Set();
    let parsedConnections = new Set();

    try {
        const fixPrompt = `A runtime exception occurred while running the app. Details: "${errorMsg}".\nPlease identify the bug in the code of the offending "${err.node_type}" node (or surrounding connections) and generate the corrected complete visual graph.`;
        const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: fixPrompt })
        });

        if (!response.ok) {
            const errText = await response.text();
            throw new Error(errText || `Server returned status ${response.status}`);
        }

        if (!response.body) throw new Error("ReadableStream not supported.");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        aiMsg.innerHTML = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            streamText += chunk;
            aiMsg.innerHTML += chunk.replace(/\n/g, '<br>');
            if (chatHistory) chatHistory.scrollTop = chatHistory.scrollHeight;

            // Real-time parsing
            const jsonStartMarker = streamText.indexOf('```json');
            let parseTarget = "";
            if (jsonStartMarker !== -1) {
                parseTarget = streamText.substring(jsonStartMarker + 7);
            } else {
                const firstBrace = streamText.indexOf('{');
                if (firstBrace !== -1) {
                    parseTarget = streamText.substring(firstBrace);
                }
            }

            if (parseTarget) {
                let depth = 0;
                let startIndices = {};
                for (let i = 0; i < parseTarget.length; i++) {
                    const char = parseTarget[i];
                    if (char === '{') {
                        depth++;
                        startIndices[depth] = i;
                    } else if (char === '}') {
                        if (startIndices[depth] !== undefined) {
                            const startIdx = startIndices[depth];
                            const objStr = parseTarget.substring(startIdx, i + 1);
                            if (depth === 2) {
                                try {
                                    const obj = JSON.parse(objStr);
                                    if (obj.type && obj.id) {
                                        if (!parsedNodeIds.has(obj.id)) {
                                            parsedNodeIds.add(obj.id);
                                            renderNode(obj);
                                        }
                                    } else {
                                        const source = obj.source || obj.from;
                                        const target = obj.target || obj.to;
                                        if (source && target) {
                                            const connKey = `${source}->${target}`;
                                            if (!parsedConnections.has(connKey)) {
                                                const normalizedConn = { source, target };
                                                if (addConnection(normalizedConn)) {
                                                    parsedConnections.add(connKey);
                                                }
                                            }
                                        }
                                    }
                                } catch (e) {}
                            }
                        }
                        depth--;
                    }
                }
            }
        }

        // Sync visual editor canvas with final generated graph from backend
        const loadedGraph = await loadGraphJSON();

        const graphPayload = loadedGraph || extractGraphJSON();
        if (graphPayload.nodes.length === 0) {
            throw new Error("No nodes were generated.");
        }

        aiMsg.innerHTML += "<br><br><span style='color: var(--accent-cyan); font-weight:700;'>⚡ Redeploying patched app...</span>";
        if (chatHistory) chatHistory.scrollTop = chatHistory.scrollHeight;

        const deployRes = await fetch('/api/deploy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(graphPayload)
        });
        const deployData = await deployRes.json();

        if (deployData.status === 'success') {
            aiMsg.innerHTML += "<br><span style='color: var(--accent-green); font-weight:700;'>✅ App successfully hot-patched and redeployed!</span>";
            let urlPath = "/";
            const urlNode = graphPayload.nodes.find(n => n.type === 'URLNode');
            if (urlNode && urlNode.config && urlNode.config.path) {
                urlPath = urlNode.config.path;
            }
            if (iframe) iframe.src = "http://localhost:8000" + urlPath;
            if (addressInput) addressInput.value = "http://localhost:8000" + urlPath;
        } else {
            aiMsg.innerHTML += `<br><span style='color: #ef4444; font-weight:700;'>❌ Redeployment of patch failed. Initiating self-heal loop...</span>`;
            await sendAutoFixPrompt(deployData.message, 1);
        }

    } catch (err) {
        aiMsg.innerHTML += `<br><span style='color: #ef4444;'>Self-Heal Error: ${err.message}</span>`;
    } finally {
        window.isHealingRuntime = false;
        if (statusIndicator) statusIndicator.className = 'status-dot';
        if (statusText) statusText.innerText = 'Connected';
        if (chatHistory) chatHistory.scrollTop = chatHistory.scrollHeight;
    }
}

function updateVisualFlow() {
    const allNodes = document.querySelectorAll('#canvas-layer > .node');

    allNodes.forEach(n => {
        n.classList.remove('status-green');
        n.classList.add('status-red');
    });

    if (!serverIsLive) {
        window.activeWires = new Set();
        wires.forEach(w => {
            w.path.classList.remove('active');
            w.path.classList.add('error');
        });
        return;
    }

    let serverNodeEl = null;
    for (let i = 0; i < allNodes.length; i++) {
        if (allNodes[i].dataset.type === 'ServerNode') {
            serverNodeEl = allNodes[i];
            break;
        }
    }

    if (!serverNodeEl) {
        window.activeWires = new Set();
        wires.forEach(w => {
            w.path.classList.remove('active');
            w.path.classList.add('error');
        });
        return;
    }

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

    window.activeWires = reachableWires;
    wires.forEach(w => {
        if (reachableWires.has(w)) {
            w.path.classList.remove('error');
            w.path.classList.add('active');
        } else {
            w.path.classList.remove('active');
            w.path.classList.add('error');
        }
    });
}

// Style nodes based on compiler errors
function updateNodeErrors() {
    document.querySelectorAll('#canvas-layer > .node.status-error').forEach(n => {
        n.classList.remove('status-error');
        const tip = n.querySelector('.__err-tip');
        if (tip) tip.remove();
    });

    if (!errorState || Object.keys(errorState).length === 0) return;

    Object.values(errorState).forEach(err => {
        const nodeType = err.node_type;
        document.querySelectorAll(`#canvas-layer > .node[data-type="${nodeType}"]`).forEach(nodeEl => {
            nodeEl.classList.add('status-error');

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

// --- CHAT & REAL-TIME PROMPT STREAMING ---
let chatHistory = document.getElementById('chat-history');
let promptInput = document.getElementById('prompt-input');
let sendBtn = document.getElementById('btn-send');
let statusIndicator = document.getElementById('status-indicator');
let statusText = document.getElementById('status-text');

async function sendPrompt() {
    const prompt = promptInput.value.trim();
    if (!prompt) return;

    const userMsg = document.createElement('div');
    userMsg.className = 'message user';
    userMsg.innerText = prompt;
    if (chatHistory) {
        chatHistory.appendChild(userMsg);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    const is_answer = waitingForAnswer;
    waitingForAnswer = false; // Reset to check if new questions are streamed

    // Clear waiting highlight
    const inputArea = document.querySelector('.chat-input-area');
    if (inputArea) inputArea.classList.remove('waiting-for-answer');

    promptInput.value = '';
    promptInput.disabled = true;
    sendBtn.disabled = true;

    if (statusIndicator) statusIndicator.className = 'status-dot generating';
    if (statusText) statusText.innerText = 'AI Thinking...';

    const aiMsg = document.createElement('div');
    aiMsg.className = 'message ai';
    aiMsg.innerHTML = 'Thinking...';
    if (chatHistory) {
        chatHistory.appendChild(aiMsg);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    let streamText = "";
    let parsedNodeIds = new Set();
    let parsedConnections = new Set();

    try {
        const graphPayload = extractGraphJSON();
        const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: prompt,
                graph: graphPayload,
                is_answer: is_answer
            })
        });

        if (!response.ok) {
            const errText = await response.text();
            throw new Error(errText || `Server returned status ${response.status}`);
        }

        if (!response.body) throw new Error("ReadableStream not supported by browser.");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        aiMsg.innerHTML = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            streamText += chunk;

            if (streamText.includes('[QUESTION]')) {
                aiMsg.className = 'message question';
                waitingForAnswer = true;
                const cleanQuestion = streamText.replace('[QUESTION]', '').trim();
                aiMsg.innerHTML = cleanQuestion.replace(/\n/g, '<br>');
            } else {
                aiMsg.innerHTML = streamText.replace(/\n/g, '<br>');
            }
            if (chatHistory) chatHistory.scrollTop = chatHistory.scrollHeight;

            // --- Real-time Depth-based Parsing (only if not waiting for answer) ---
            if (!waitingForAnswer) {
                const jsonStartMarker = streamText.indexOf('```json');
                let parseTarget = "";
                if (jsonStartMarker !== -1) {
                    parseTarget = streamText.substring(jsonStartMarker + 7);
                } else {
                    const firstBrace = streamText.indexOf('{');
                    if (firstBrace !== -1) {
                        parseTarget = streamText.substring(firstBrace);
                    }
                }

                if (parseTarget) {
                    let depth = 0;
                    let startIndices = {};
                    for (let i = 0; i < parseTarget.length; i++) {
                        const char = parseTarget[i];
                        if (char === '{') {
                            depth++;
                            startIndices[depth] = i;
                        } else if (char === '}') {
                            if (startIndices[depth] !== undefined) {
                                const startIdx = startIndices[depth];
                                const objStr = parseTarget.substring(startIdx, i + 1);
                                if (depth === 2) {
                                    try {
                                        const obj = JSON.parse(objStr);
                                        if (obj.type && obj.id) {
                                            if (!parsedNodeIds.has(obj.id)) {
                                                parsedNodeIds.add(obj.id);
                                                renderNode(obj);
                                            }
                                        } else {
                                            const source = obj.source || obj.from;
                                            const target = obj.target || obj.to;
                                            if (source && target) {
                                                const connKey = `${source}->${target}`;
                                                if (!parsedConnections.has(connKey)) {
                                                    const normalizedConn = { source, target };
                                                    if (addConnection(normalizedConn)) {
                                                        parsedConnections.add(connKey);
                                                    }
                                                }
                                            }
                                        }
                                    } catch (e) {
                                        // Ignore partial parsing errors
                                    }
                                }
                            }
                            depth--;
                        }
                    }
                }
            }
        }

        if (waitingForAnswer) {
            if (inputArea) inputArea.classList.add('waiting-for-answer');
            if (promptInput) {
                promptInput.placeholder = "Please answer the clarifying question(s) above...";
                promptInput.disabled = false;
            }
            if (sendBtn) sendBtn.disabled = false;
            return;
        }

        // Sync visual editor canvas with final generated graph from backend
        const loadedGraph = await loadGraphJSON();

        // 3. Trigger compile and save using the exact loaded graph from backend
        const finalPayload = loadedGraph || extractGraphJSON();

        if (finalPayload.nodes.length === 0) {
            throw new Error("No nodes were generated. Verify backend configuration.");
        }

        aiMsg.innerHTML += "<br><br><span style='color: var(--accent-cyan); font-weight:700;'>⚡ Deploying app...</span>";
        if (chatHistory) chatHistory.scrollTop = chatHistory.scrollHeight;

        const deployRes = await fetch('/api/deploy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(finalPayload)
        });
        const deployData = await deployRes.json();

        if (deployData.status === 'success') {
            aiMsg.innerHTML += "<br><span style='color: var(--accent-green); font-weight:700;'>✅ App deployed successfully!</span>";
            let urlPath = "/";
            const urlNode = finalPayload.nodes.find(n => n.type === 'URLNode');
            if (urlNode && urlNode.config && urlNode.config.path) {
                urlPath = urlNode.config.path;
            }
            if (iframe) iframe.src = "http://localhost:8000" + urlPath;
            if (addressInput) addressInput.value = "http://localhost:8000" + urlPath;
        } else {
            aiMsg.innerHTML += `<br><span style='color: #ef4444; font-weight:700;'>❌ Deployment Error: ${deployData.message}</span>`;
            await sendAutoFixPrompt(deployData.message, 1);
        }

    } catch (err) {
        aiMsg.innerHTML = `<span style='color: #ef4444;'>Error: ${err.message}</span>`;
    } finally {
        if (!waitingForAnswer) {
            promptInput.placeholder = "e.g., Make a cool AI blog page with a blue cyberpunk CSS styling...";
            promptInput.disabled = false;
            sendBtn.disabled = false;
        }
        if (statusIndicator) statusIndicator.className = 'status-dot';
        if (statusText) statusText.innerText = 'Connected';
        if (chatHistory) chatHistory.scrollTop = chatHistory.scrollHeight;
    }
}


async function sendAutoFixPrompt(errorMessage, retryCount = 1) {
    if (retryCount > 5) {
        const aiMsg = document.createElement('div');
        aiMsg.className = 'message ai';
        aiMsg.innerHTML = `<span style='color: #ef4444; font-weight:700;'>❌ Auto-fix reached maximum retries (5). Please fix manually.</span>`;
        if (chatHistory) {
            chatHistory.appendChild(aiMsg);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }
        return;
    }

    const systemMsg = document.createElement('div');
    systemMsg.className = 'message user';
    systemMsg.style.background = 'rgba(239, 68, 68, 0.1)';
    systemMsg.style.border = '1px solid rgba(239, 68, 68, 0.3)';
    systemMsg.style.color = '#f87171';
    systemMsg.innerHTML = `⚠️ <b>[Auto-Fix Attempt ${retryCount}/5]</b> Deployment failed:<br><code>${errorMessage}</code><br>Asking AI to heal the graph...`;
    if (chatHistory) {
        chatHistory.appendChild(systemMsg);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    if (statusIndicator) statusIndicator.className = 'status-dot generating';
    if (statusText) statusText.innerText = 'AI Self-Healing...';

    const aiMsg = document.createElement('div');
    aiMsg.className = 'message ai';
    aiMsg.innerHTML = 'Analyzing error and correcting graph...';
    if (chatHistory) {
        chatHistory.appendChild(aiMsg);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    let streamText = "";
    let parsedNodeIds = new Set();
    let parsedConnections = new Set();

    try {
        const fixPrompt = `The deployment failed with this compilation/validation error: "${errorMessage}".\nPlease fix this error by generating the corrected visual node graph. Ensure all required nodes are connected correctly and code is valid.`;
        const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: fixPrompt })
        });

        if (!response.ok) {
            const errText = await response.text();
            throw new Error(errText || `Server returned status ${response.status}`);
        }

        if (!response.body) throw new Error("ReadableStream not supported by browser.");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        aiMsg.innerHTML = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            streamText += chunk;
            aiMsg.innerHTML += chunk.replace(/\n/g, '<br>');
            if (chatHistory) chatHistory.scrollTop = chatHistory.scrollHeight;

            // Real-time parsing
            const jsonStartMarker = streamText.indexOf('```json');
            let parseTarget = "";
            if (jsonStartMarker !== -1) {
                parseTarget = streamText.substring(jsonStartMarker + 7);
            } else {
                const firstBrace = streamText.indexOf('{');
                if (firstBrace !== -1) {
                    parseTarget = streamText.substring(firstBrace);
                }
            }

            if (parseTarget) {
                let depth = 0;
                let startIndices = {};
                for (let i = 0; i < parseTarget.length; i++) {
                    const char = parseTarget[i];
                    if (char === '{') {
                        depth++;
                        startIndices[depth] = i;
                    } else if (char === '}') {
                        if (startIndices[depth] !== undefined) {
                            const startIdx = startIndices[depth];
                            const objStr = parseTarget.substring(startIdx, i + 1);
                            if (depth === 2) {
                                try {
                                    const obj = JSON.parse(objStr);
                                    if (obj.type && obj.id) {
                                        if (!parsedNodeIds.has(obj.id)) {
                                            parsedNodeIds.add(obj.id);
                                            renderNode(obj);
                                        }
                                    } else {
                                        const source = obj.source || obj.from;
                                        const target = obj.target || obj.to;
                                        if (source && target) {
                                            const connKey = `${source}->${target}`;
                                            if (!parsedConnections.has(connKey)) {
                                                const normalizedConn = { source, target };
                                                if (addConnection(normalizedConn)) {
                                                    parsedConnections.add(connKey);
                                                }
                                            }
                                        }
                                    }
                                } catch (e) {}
                            }
                        }
                        depth--;
                    }
                }
            }
        }

        // Sync visual editor canvas with final generated graph from backend
        const loadedGraph = await loadGraphJSON();

        const graphPayload = loadedGraph || extractGraphJSON();
        if (graphPayload.nodes.length === 0) {
            throw new Error("No nodes were generated during fix.");
        }

        aiMsg.innerHTML += "<br><br><span style='color: var(--accent-cyan); font-weight:700;'>⚡ Redeploying app...</span>";
        if (chatHistory) chatHistory.scrollTop = chatHistory.scrollHeight;

        const deployRes = await fetch('/api/deploy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(graphPayload)
        });
        const deployData = await deployRes.json();

        if (deployData.status === 'success') {
            aiMsg.innerHTML += "<br><span style='color: var(--accent-green); font-weight:700;'>✅ App self-healed and deployed successfully!</span>";
            let urlPath = "/";
            const urlNode = graphPayload.nodes.find(n => n.type === 'URLNode');
            if (urlNode && urlNode.config && urlNode.config.path) {
                urlPath = urlNode.config.path;
            }
            if (iframe) iframe.src = "http://localhost:8000" + urlPath;
            if (addressInput) addressInput.value = "http://localhost:8000" + urlPath;
        } else {
            aiMsg.innerHTML += `<br><span style='color: #ef4444; font-weight:700;'>❌ Redeployment failed. Retrying...</span>`;
            await sendAutoFixPrompt(deployData.message, retryCount + 1);
        }

    } catch (err) {
        aiMsg.innerHTML += `<br><span style='color: #ef4444;'>Auto-Fix Error: ${err.message}</span>`;
        await sendAutoFixPrompt(err.message, retryCount + 1);
    } finally {
        if (statusIndicator) statusIndicator.className = 'status-dot';
        if (statusText) statusText.innerText = 'Connected';
        if (chatHistory) chatHistory.scrollTop = chatHistory.scrollHeight;
    }
}

// --- HELPER FOR AI LIVE GENERATION ---
function renderNode(node) {
    let el = document.getElementById(node.id);
    if (el) {
        updateNodeConfigValues(el, node);
        return;
    }

    const template = document.querySelector(`#node-templates [data-type="${node.type}"]`);
    if (!template) return;

    el = template.cloneNode(true);
    el.id = node.id;
    el.style.left = `${node.x || 100}px`;
    el.style.top = `${node.y || 100}px`;

    el.querySelectorAll('.port').forEach(port => {
        port.dataset.node = node.id;
    });

    canvasLayer.appendChild(el);
    bindNodeEvents(el);

    if (['LogicNode', 'ContextNode', 'RenderNode', 'CSSNode', 'JSNode'].includes(node.type)) {
        initMonacoEditor(el, node.type);
    }

    updateNodeConfigValues(el, node);
    updateAllWires();
}

function updateNodeConfigValues(nodeEl, nodeData) {
    const config = nodeData.config || {};
    const type = nodeData.type;

    nodeEl._loadedConfig = config;

    if (type === 'ServerNode') {
        const ipEl = nodeEl.querySelector('.ip-input');
        const portEl = nodeEl.querySelector('.port-input');
        if (ipEl && config.ip !== undefined) ipEl.value = config.ip;
        if (portEl && config.port !== undefined) portEl.value = config.port;
    } else if (type === 'URLNode') {
        const pathEl = nodeEl.querySelector('.path-input');
        if (pathEl && config.path !== undefined) pathEl.value = config.path;
    } else if (type === 'ModelNode') {
        const queryEl = nodeEl.querySelector('.query-input');
        const paramsEl = nodeEl.querySelector('.params-input');
        const contextEl = nodeEl.querySelector('.context-input');
        const isWriteEl = nodeEl.querySelector('.is-write-input');
        if (queryEl && config.query !== undefined) queryEl.value = config.query;
        if (paramsEl && config.paramsMap !== undefined) paramsEl.value = config.paramsMap;
        if (contextEl && config.contextKey !== undefined) contextEl.value = config.contextKey;
        if (isWriteEl && config.isWrite !== undefined) isWriteEl.checked = config.isWrite;
    } else if (type === 'RenderNode') {
        const filenameEl = nodeEl.querySelector('.filename-input');
        if (filenameEl && config.filename !== undefined) filenameEl.value = config.filename;
        if (config.html_code) {
            _setMonacoValueWithRetry(nodeEl, config.html_code, 'html');
        }
    } else if (type === 'LogicNode' || type === 'ContextNode' || type === 'JSNode') {
        if (config.code) {
            const lang = type === 'JSNode' ? 'javascript' : 'python';
            _setMonacoValueWithRetry(nodeEl, config.code, lang);
        }
    } else if (type === 'CSSNode') {
        const cssFilenameEl = nodeEl.querySelector('.css-filename-input');
        if (cssFilenameEl && config.css_filename !== undefined) cssFilenameEl.value = config.css_filename;
        if (config.css_code) {
            _setMonacoValueWithRetry(nodeEl, config.css_code, 'css');
        }
    }
}

function addConnection(conn) {
    const sourceId = conn.source || conn.from;
    const targetId = conn.target || conn.to;
    if (!sourceId || !targetId) return false;

    // Check if wire already exists
    const exists = wires.some(w => w.sourceNode === sourceId && w.targetNode === targetId);
    if (exists) return true;

    const sourceEl = document.getElementById(sourceId);
    const targetEl = document.getElementById(targetId);
    if (!sourceEl || !targetEl) return false;

    const fromPort = sourceEl.querySelector('.out-port');
    const toPort = targetEl.querySelector('.in-port');
    if (fromPort && toPort) {
        createWire(fromPort, toPort);
        return true;
    }
    return false;
}

// Start visual editor and polling
init();
setInterval(pollServerStatus, 2000);
pollServerStatus();

// --- AI PROVIDER SETTINGS CONTROLLER ---
function toggleProviderFields() {
    const selectedProvider = document.getElementById('provider-select').value;
    document.querySelectorAll('.provider-fields-group').forEach(group => {
        if (group.dataset.provider === selectedProvider) {
            group.classList.add('active');
        } else {
            group.classList.remove('active');
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
            document.getElementById('settings-modal').classList.remove('hidden');
        })
        .catch(err => {
            alert('Failed to load settings: ' + err.message);
        });
}

function closeSettings() {
    document.getElementById('settings-modal').classList.add('hidden');
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
            alert('Settings saved successfully and settings.py / .env updated!');
            updateActiveModelDisplay(payload);
            closeSettings();
        } else {
            alert('Failed to save settings: ' + (data.message || 'unknown error'));
        }
    })
    .catch(err => {
        alert('Error saving settings: ' + err.message);
    });
}

function updateActiveModelDisplay(data) {
    const provider = data.SELECTED_AI_PROVIDER || 'ollama';
    let modelName = provider.toUpperCase();
    if (provider === 'ollama') modelName = data.OLLAMA_MODEL || 'gemma4:26b';
    else if (provider === 'gemini') modelName = data.GEMINI_MODEL || 'gemini-1.5-flash';
    else if (provider === 'gpt') modelName = data.OPENAI_MODEL || 'gpt-4o-mini';
    else if (provider === 'claude') modelName = data.CLAUDE_MODEL || 'claude-3-5-sonnet-20241022';
    else if (provider === 'deepseek') modelName = data.DEEPSEEK_MODEL || 'deepseek-chat';
    else if (provider === 'openrouter') modelName = data.OPENROUTER_MODEL || 'google/gemini-2.0-flash-exp:free';
    else if (provider === 'nvidia') modelName = data.NVIDIA_MODEL || 'qwen/qwen3-coder-480b-a35b-instruct';
    else if (provider === 'glm') modelName = data.GLM_MODEL || 'glm-4-flash';
    else if (provider === 'dough') modelName = data.DOUGH_MODEL || 'deepseek-chat';
    else if (provider === 'custom') modelName = data.CUSTOM_MODEL || 'custom-model';
    
    const display = document.getElementById('active-model-display');
    if (display) display.innerText = modelName;
}

// --- RESET SERVER GRAPH BINDING ---
const btnResetGraph = document.getElementById('btn-reset-graph');
if (btnResetGraph) {
    btnResetGraph.addEventListener('click', async () => {
        if (!confirm("Are you sure you want to completely clear graph.json from disk and reset the editor? This cannot be undone.")) {
            return;
        }
        try {
            const res = await fetch('/api/clear-graph', { method: 'POST' });
            const data = await res.json();
            if (data.status === 'success') {
                resetCanvas();
                alert('Graph JSON has been completely reset to empty!');
            } else {
                alert('Failed to reset graph: ' + data.message);
            }
        } catch (err) {
            alert('Error resetting graph: ' + err.message);
        }
    });
}

async function clearChat() {
    if (!confirm("Are you sure you want to start a new chat? This will clear your chat memory and session state, allowing you to start fresh without prior context interfering.")) {
        return;
    }
    try {
        const res = await fetch('/api/chat/clear', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            // Restore default welcome message
            if (chatHistory) {
                chatHistory.innerHTML = `
                    <div class="message ai">
                        Hello! Describe the website or API you want to build. I will draft the nodes, build the architecture, and launch the preview in real-time.
                    </div>
                `;
            }
            // Reset state variables
            waitingForAnswer = false;
            // Restore textarea input placeholder and state
            if (promptInput) {
                promptInput.value = '';
                promptInput.placeholder = "e.g., Make a cool AI blog page with a blue cyberpunk CSS styling...";
                promptInput.disabled = false;
            }
            const inputArea = document.querySelector('.chat-input-area');
            if (inputArea) {
                inputArea.classList.remove('waiting-for-answer');
            }
            if (sendBtn) {
                sendBtn.disabled = false;
            }
            alert('Chat session cleared successfully!');
        } else {
            alert('Failed to clear chat session: ' + data.message);
        }
    } catch (err) {
        alert('Error clearing chat session: ' + err.message);
    }
}


