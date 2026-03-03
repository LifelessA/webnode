// State
let panX = 0, panY = 0, scale = 1;
let isPanning = false, startX, startY;
let activeNode = null;
let isWiring = false;
let startPort = null;
let wires = [];
let nodeIdCounter = 10;

const canvasLayer = document.getElementById('canvas-layer');
const canvasContainer = document.getElementById('canvas-container');
const wireLayer = document.getElementById('wire-layer');

function init() {
    document.querySelectorAll('#canvas-layer .node').forEach(node => bindNodeEvents(node));
    updateAllWires();
    wireLayer.addEventListener('dblclick', (e) => {
        if (e.target.classList.contains('wire')) deleteWire(e.target);
    });
    loadGraphJSON();
}

canvasContainer.addEventListener('mousedown', (e) => {
    if (e.target.closest('.node') || e.target.closest('.port')) return;
    if (e.button === 1 || e.button === 0) {
        isPanning = true;
        startX = e.clientX - panX;
        startY = e.clientY - panY;
    }
});

window.addEventListener('mousemove', (e) => {
    if (isPanning) { panX = e.clientX - startX; panY = e.clientY - startY; updateCanvasTransform(); }
    if (isWiring && startPort) drawTempWire(e.clientX, e.clientY);
});

window.addEventListener('mouseup', () => { isPanning = false; stopWiring(); });

canvasContainer.addEventListener('wheel', (e) => {
    if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        const zoomIntensity = 0.1;
        const wheel = e.deltaY < 0 ? 1 : -1;
        let newScale = scale * Math.exp(wheel * zoomIntensity);
        newScale = Math.min(Math.max(0.2, newScale), 3);
        scale = newScale;
        updateCanvasTransform();
    }
});

function updateCanvasTransform() {
    canvasLayer.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
    updateAllWires();
}

function bindNodeEvents(node) {
    const header = node.querySelector('.node-header');
    if (header) header.addEventListener('mousedown', startNodeDrag);
    node.querySelectorAll('.port').forEach(port => {
        port.addEventListener('mousedown', onPortMouseDown);
        port.addEventListener('mouseup', onPortMouseUp);
    });
    node.addEventListener('dblclick', (e) => {
        if (e.target.classList.contains('port') || e.target.closest('input') || e.target.closest('button') || e.target.closest('.monaco-container')) return;
        if (confirm('Delete this node?')) deleteNode(node.id);
    });
}

function deleteNode(nodeId) {
    const nodeEl = document.getElementById(nodeId);
    if (!nodeEl) return;
    wires = wires.filter(w => {
        if (w.sourceNode === nodeId || w.targetNode === nodeId) { w.path.remove(); return false; }
        return true;
    });
    nodeEl.remove();
}

function deleteWire(pathEl) {
    wires = wires.filter(w => { if (w.path === pathEl) { w.path.remove(); return false; } return true; });
}

document.querySelectorAll('.palette-node').forEach(item => {
    item.addEventListener('dragstart', (e) => { e.dataTransfer.setData('text/plain', e.target.getAttribute('data-type')); });
});

canvasContainer.addEventListener('dragover', (e) => { e.preventDefault(); });

canvasContainer.addEventListener('drop', (e) => {
    e.preventDefault();
    const nodeType = e.dataTransfer.getData('text/plain');
    if (!nodeType) return;
    const template = document.querySelector(`#node-templates [data-type="${nodeType}"]`);
    if (!template) return;
    const newNode = template.cloneNode(true);
    const newId = `node-${nodeIdCounter++}`;
    newNode.id = newId;
    newNode.querySelectorAll('.port').forEach(port => { port.dataset.node = newId; });
    const rect = canvasLayer.getBoundingClientRect();
    newNode.style.left = `${(e.clientX - rect.left) / scale}px`;
    newNode.style.top = `${(e.clientY - rect.top) / scale}px`;
    canvasLayer.appendChild(newNode);
    bindNodeEvents(newNode);
    if (['LogicNode', 'ContextNode', 'RenderNode'].includes(nodeType)) initMonacoEditor(newNode, nodeType);
});

function initMonacoEditor(nodeElement, type) {
    const container = nodeElement.querySelector('.monaco-container');
    if (!container) return;
    let initConfig = { value: '', language: 'python', theme: 'vs-dark', minimap: { enabled: false }, scrollBeyondLastLine: false, fontSize: 12 };
    if (type === 'LogicNode') {
        initConfig.value = 'def process_logic(request):\n    # Write Python logic here\n    return {}';
    } else if (type === 'ContextNode') {
        initConfig.value = 'def node_logic(request):\n    return {"key": "value"}';
    } else if (type === 'RenderNode') {
        initConfig.value = '<!DOCTYPE html>\n<html>\n<body>\n    {result}\n</body>\n</html>';
        initConfig.language = 'html';
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

function startNodeDrag(e) {
    if (e.target.classList.contains('port')) return;
    activeNode = e.target.closest('.node');
    canvasLayer.appendChild(activeNode);
    const rect = activeNode.getBoundingClientRect();
    const offsetX = (e.clientX - rect.left) / scale;
    const offsetY = (e.clientY - rect.top) / scale;
    function onMouseMove(moveEvent) {
        const canvasRect = canvasLayer.getBoundingClientRect();
        activeNode.style.left = `${(moveEvent.clientX - canvasRect.left) / scale - offsetX}px`;
        activeNode.style.top = `${(moveEvent.clientY - canvasRect.top) / scale - offsetY}px`;
        updateAllWires();
    }
    function onMouseUp() {
        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('mouseup', onMouseUp);
        activeNode = null;
    }
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
}

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
        if (startPort.classList.contains('out-port') && e.target.classList.contains('in-port') && startPort.dataset.node !== e.target.dataset.node) {
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
    return { x: rect.left - canvasRect.left + (rect.width / 2), y: rect.top - canvasRect.top + (rect.height / 2) };
}

function drawTempWire(mouseX, mouseY) {
    if (!startPort) return;
    const start = getPortCoords(startPort);
    const canvasRect = canvasContainer.getBoundingClientRect();
    drawBezier(document.getElementById('temp-wire'), start.x, start.y, mouseX - canvasRect.left, mouseY - canvasRect.top);
}

function createWire(fromPort, toPort) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.classList.add('wire');
    wireLayer.appendChild(path);
    wires.push({ sourceNode: fromPort.dataset.node, sourcePort: fromPort.dataset.port, targetNode: toPort.dataset.node, targetPort: toPort.dataset.port, path: path, fromEl: fromPort, toEl: toPort });
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
    pathEl.setAttribute('d', `M ${x1} ${y1} C ${x1 + curvature} ${y1}, ${x2 - curvature} ${y2}, ${x2} ${y2}`);
}

async function loadGraphJSON() {
    try {
        const res = await fetch('/api/load');
        const data = await res.json();
        if (!data || !data.nodes || data.nodes.length === 0) return;
        document.querySelectorAll('#canvas-layer .node').forEach(n => n.remove());
        document.querySelectorAll('#wire-layer .wire').forEach(w => w.remove());
        wires = [];
        let maxId = 10;
        data.nodes.forEach(nodeData => {
            const template = document.querySelector(`#node-templates [data-type="${nodeData.type}"]`);
            if (!template) return;
            const newNode = template.cloneNode(true);
            newNode.id = nodeData.id;
            const nId = parseInt(nodeData.id.replace('node-', ''));
            if (!isNaN(nId) && nId > maxId) maxId = nId;
            newNode.querySelectorAll('.port').forEach(port => { port.dataset.node = nodeData.id; });
            newNode.style.left = `${nodeData.x}px`;
            newNode.style.top = `${nodeData.y}px`;
            canvasLayer.appendChild(newNode);
            bindNodeEvents(newNode);
            if (['LogicNode', 'ContextNode', 'RenderNode'].includes(nodeData.type)) initMonacoEditor(newNode, nodeData.type);
            setTimeout(() => {
                const config = nodeData.config || {};
                const type = nodeData.type;
                if (type === 'ServerNode') {
                    if (config.ip) newNode.querySelector('.ip-input').value = config.ip;
                    if (config.port) newNode.querySelector('.port-input').value = config.port;
                } else if (type === 'URLNode') {
                    if (config.path) newNode.querySelector('.path-input').value = config.path;
                } else if (type === 'ModelNode') {
                    if (config.query) newNode.querySelector('.query-input').value = config.query;
                    if (config.paramsMap) newNode.querySelector('.params-input').value = config.paramsMap;
                    if (config.contextKey) newNode.querySelector('.context-input').value = config.contextKey;
                    if (config.isWrite !== undefined) newNode.querySelector('.is-write-input').checked = config.isWrite;
                } else if (type === 'RenderNode') {
                    if (config.filename) newNode.querySelector('.filename-input').value = config.filename;
                    if (config.html_code && newNode._monacoEditor) newNode._monacoEditor.setValue(config.html_code);
                } else if (type === 'LogicNode' || type === 'ContextNode') {
                    if (config.code && newNode._monacoEditor) newNode._monacoEditor.setValue(config.code);
                }
            }, 100);
        });
        nodeIdCounter = maxId + 1;
        setTimeout(() => {
            data.connections.forEach(conn => {
                const sourceNodeEl = document.getElementById(conn.source);
                const targetNodeEl = document.getElementById(conn.target);
                if (!sourceNodeEl || !targetNodeEl) return;
                const fromPort = sourceNodeEl.querySelector('.out-port');
                const toPort = targetNodeEl.querySelector('.in-port');
                if (fromPort && toPort) createWire(fromPort, toPort);
            });
            updateAllWires();
        }, 150);
    } catch (e) {
        console.error("Failed to load graph:", e);
    }
}

function extractGraphJSON() {
    const nodes = [];
    document.querySelectorAll('#canvas-layer .node').forEach(nodeEl => {
        const id = nodeEl.id;
        const type = nodeEl.dataset.type;
        const x = parseFloat(nodeEl.style.left) || 0;
        const y = parseFloat(nodeEl.style.top) || 0;
        let config = {};
        if (type === 'ServerNode') { config.ip = nodeEl.querySelector('.ip-input').value; config.port = parseInt(nodeEl.querySelector('.port-input').value, 10); }
        else if (type === 'URLNode') { config.path = nodeEl.querySelector('.path-input').value; }
        else if (type === 'RenderNode') { config.filename = nodeEl.querySelector('.filename-input').value; if (nodeEl._monacoEditor) config.html_code = nodeEl._monacoEditor.getValue(); }
        else if (type === 'ModelNode') { config.query = nodeEl.querySelector('.query-input').value; config.paramsMap = nodeEl.querySelector('.params-input').value; config.contextKey = nodeEl.querySelector('.context-input').value; config.isWrite = nodeEl.querySelector('.is-write-input').checked; }
        else if (type === 'LogicNode' || type === 'ContextNode') { if (nodeEl._monacoEditor) config.code = nodeEl._monacoEditor.getValue(); }
        nodes.push({ id, type, x, y, config });
    });
    const connections = wires.map(w => ({ source: w.sourceNode, target: w.targetNode }));
    return { nodes, connections };
}

document.getElementById('btn-save').addEventListener('click', async () => {
    const payload = extractGraphJSON();
    try {
        await fetch('/api/save', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        alert('Graph JSON saved!');
    } catch (e) { alert('Failed to save. Is node_backend.py running?'); }
});

document.getElementById('btn-deploy').addEventListener('click', async () => {
    const payload = extractGraphJSON();
    try {
        const res = await fetch('/api/deploy', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const result = await res.json();
        if (result.status === 'success') {
            document.getElementById('status-indicator').innerText = '● Live';
            document.getElementById('status-indicator').className = 'live';
            alert('Deployed! main.py generated and server is running.');
        } else { alert('Failed to deploy: ' + result.message); }
    } catch (e) { alert('Cannot connect to backend compiler.'); }
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

async function pollServerStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        const isLive = (data.status === 'live');
        updateVisualFlow(isLive);
        const indicator = document.getElementById('status-indicator');
        if (isLive) { indicator.innerText = '● Live'; indicator.className = 'live'; }
        else { indicator.innerText = '● Offline'; indicator.className = ''; }
    } catch (e) { updateVisualFlow(false); }
}

function updateVisualFlow(isLive) {
    const allNodes = document.querySelectorAll('#canvas-layer > .node');
    allNodes.forEach(n => { n.classList.remove('status-green'); n.classList.add('status-red'); });
    wires.forEach(w => { w.path.classList.remove('active'); w.path.classList.add('error'); });
    if (!isLive) return;
    let serverNodeEl = null;
    for (let i = 0; i < allNodes.length; i++) { if (allNodes[i].dataset.type === 'ServerNode') { serverNodeEl = allNodes[i]; break; } }
    if (!serverNodeEl) return;
    const reachableNodes = new Set();
    const reachableWires = new Set();
    reachableNodes.add(serverNodeEl.id);
    const queue = [serverNodeEl.id];
    while (queue.length > 0) {
        const curr = queue.shift();
        wires.forEach(w => {
            if (w.sourceNode === curr) { reachableWires.add(w); if (!reachableNodes.has(w.targetNode)) { reachableNodes.add(w.targetNode); queue.push(w.targetNode); } }
        });
    }
    allNodes.forEach(n => { if (reachableNodes.has(n.id)) { n.classList.remove('status-red'); n.classList.add('status-green'); } });
    wires.forEach(w => { if (reachableWires.has(w)) { w.path.classList.remove('error'); w.path.classList.add('active'); } });
}

setInterval(pollServerStatus, 2000);
init();
