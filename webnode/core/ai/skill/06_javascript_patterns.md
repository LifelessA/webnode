# JAVASCRIPT PATTERNS SKILL

## Initialization Pattern (ALWAYS wrap in DOMContentLoaded)
```javascript
document.addEventListener('DOMContentLoaded', () => {
  // All initialization code here
  init();
});
```

## Dynamic List Item Creation (use classes NOT inline styles)
```javascript
function createTaskElement(task) {
  const item = document.createElement('div');
  item.className = 'list-item';
  item.dataset.id = task.id;
  item.style.animationDelay = `${index * 60}ms`;
  item.innerHTML = `
    <input type="checkbox" class="task-checkbox" ${task.done ? 'checked' : ''}>
    <span class="item-text ${task.done ? 'completed' : ''}">${escapeHtml(task.text)}</span>
    <button class="btn-ghost delete-btn" style="padding:6px 10px;font-size:12px">✕</button>
  `;
  item.querySelector('.task-checkbox').addEventListener('change', () => toggleTask(task.id));
  item.querySelector('.delete-btn').addEventListener('click', () => deleteTask(task.id));
  return item;
}

function escapeHtml(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}
```

## localStorage Pattern (always use try/catch)
```javascript
const STORAGE_KEY = 'app_data_v1';

function saveToStorage(data) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(data)); } catch(e) { console.warn('Storage failed:', e); }
}

function loadFromStorage(fallback = []) {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) ?? fallback; } catch { return fallback; }
}
```

## Game Loop Pattern (single setInterval — NOT recursive setTimeout)
```javascript
let gameState = { running: false, score: 0, intervalId: null };

function startGame() {
  if (gameState.intervalId) clearInterval(gameState.intervalId);
  gameState.running = true;
  gameState.score = 0;
  gameState.intervalId = setInterval(gameLoop, 100);
}

function gameLoop() {
  if (!gameState.running) return;
  update();
  render();
}

function stopGame() {
  gameState.running = false;
  if (gameState.intervalId) { clearInterval(gameState.intervalId); gameState.intervalId = null; }
  showOverlay('Game Over', gameState.score);
}
```

## Overlay Show/Hide Pattern
```javascript
function showOverlay(title, score) {
  const overlay = document.getElementById('overlay');
  document.getElementById('overlay-title').textContent = title;
  if (document.getElementById('final-score')) document.getElementById('final-score').textContent = score;
  overlay.style.display = 'flex';
}

function hideOverlay() {
  document.getElementById('overlay').style.display = 'none';
}
```

## Event Delegation (for dynamic lists)
```javascript
document.getElementById('task-list').addEventListener('click', (e) => {
  const item = e.target.closest('.list-item');
  if (!item) return;
  const id = item.dataset.id;
  if (e.target.classList.contains('delete-btn')) deleteTask(id);
  if (e.target.classList.contains('task-checkbox')) toggleTask(id);
});
```
