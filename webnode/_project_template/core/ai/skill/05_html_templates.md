# HTML TEMPLATE PATTERNS SKILL

## Mandatory HTML Head (every page)
```html
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#080b14">
  <title>Page Title</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;700;800;900&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/CSSFILENAME.css">
</head>
```
Replace CSSFILENAME with the actual CSSNode filename from the SEED path.

## Todo / Task Manager
```html
<div class="app-wrapper">
  <div class="app-container">
    <div class="app-header" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:var(--space-6)">
      <h1 class="heading-gradient">My Tasks</h1>
      <span class="badge" id="task-count">0 tasks</span>
    </div>
    <div class="input-row" style="display:flex;gap:var(--space-3);margin-bottom:var(--space-4)">
      <input type="text" id="task-input" class="input-field" placeholder="Add a new task...">
      <button id="add-btn" class="btn-primary">Add</button>
    </div>
    <div class="divider"></div>
    <div id="filter-row" style="display:flex;gap:var(--space-2);margin-bottom:var(--space-4)">
      <button class="btn-ghost active-filter" data-filter="all">All</button>
      <button class="btn-ghost" data-filter="active">Active</button>
      <button class="btn-ghost" data-filter="done">Done</button>
    </div>
    <div id="task-list"></div>
    <div id="empty-state" style="text-align:center;padding:var(--space-10);color:var(--text-muted);display:none">
      No tasks yet. Add one above!
    </div>
  </div>
</div>
```

## Game / Canvas
```html
<div class="app-wrapper">
  <div class="app-container" style="max-width:460px">
    <div class="game-header" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:var(--space-5)">
      <h1 class="heading-gradient">Game Title</h1>
      <div style="display:flex;gap:var(--space-2)">
        <span class="badge" id="score-badge">Score: <b id="score">0</b></span>
        <span class="badge warning" id="best-badge">Best: <b id="best-score">0</b></span>
      </div>
    </div>
    <div class="canvas-wrapper" style="position:relative;border-radius:var(--radius-lg);overflow:hidden">
      <canvas id="gameCanvas" width="400" height="400" style="display:block;width:100%"></canvas>
      <div id="overlay" class="glass-card hidden" style="position:absolute;inset:0;display:none;flex-direction:column;align-items:center;justify-content:center;gap:var(--space-4);border-radius:0">
        <h2 class="heading-gradient" id="overlay-title">Game Over</h2>
        <p style="color:var(--text-muted)">Final Score: <strong id="final-score">0</strong></p>
        <button id="restart-btn" class="btn-primary">Play Again</button>
      </div>
    </div>
  </div>
</div>
```

## Dashboard
```html
<div class="dashboard-layout">
  <aside class="sidebar">
    <div class="heading-gradient" style="font-size:1.4rem;font-weight:800;margin-bottom:var(--space-8)">AppName</div>
    <nav style="display:flex;flex-direction:column;gap:var(--space-1)">
      <a href="#" class="nav-item" style="padding:var(--space-3) var(--space-4);border-radius:var(--radius-md);color:var(--text-muted);text-decoration:none;transition:all 0.2s;font-size:14px">Dashboard</a>
    </nav>
  </aside>
  <main class="main-content">
    <h1 class="heading-xl" style="margin-bottom:var(--space-8)">Dashboard</h1>
    <div class="bento-grid" id="stats-grid"></div>
  </main>
</div>
```
