# LAYOUT PATTERNS SKILL

Choose the layout pattern that best fits the requested feature and apply it.

## Pattern A — Centered App (tools, games, forms, calculators)
```css
.app-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-6);
  background:
    radial-gradient(ellipse at 50% 0%, rgba(99,102,241,0.12) 0%, transparent 60%),
    var(--bg);
}
.app-container {
  width: 100%;
  max-width: 520px;
  background: var(--surface);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-2);
  border-radius: var(--radius-xl);
  padding: var(--space-8);
  box-shadow: var(--shadow-lg), 0 0 0 1px rgba(255,255,255,0.03);
  animation: fadeUp 0.5s ease both;
}
```

## Pattern B — Dashboard (sidebar + main content)
```css
.dashboard-layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  min-height: 100vh;
}
.sidebar {
  background: var(--bg-2);
  border-right: 1px solid var(--border);
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  position: sticky;
  top: 0;
  height: 100vh;
}
.main-content { padding: var(--space-8); overflow-y: auto; }
```

## Pattern C — Landing Page (hero + sections)
```css
.hero-section {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--space-12) var(--space-6);
  background: radial-gradient(ellipse 80% 60% at 50% -10%, rgba(99,102,241,0.25) 0%, transparent 70%);
  position: relative;
}
.hero-section::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, rgba(255,255,255,0.025) 1px, transparent 1px);
  background-size: 32px 32px;
  pointer-events: none;
}
```

## Pattern D — Bento Grid (card-based layouts)
```css
.bento-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-auto-rows: minmax(160px, auto);
  gap: var(--space-4);
}
.bento-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  transition: border-color 0.2s, transform 0.2s, box-shadow 0.2s;
}
.bento-card:hover { border-color: var(--border-2); transform: translateY(-2px); box-shadow: var(--shadow-md); }
.bento-card.wide  { grid-column: span 2; }
.bento-card.tall  { grid-row: span 2; }
```

## Responsive (ALWAYS include)
```css
@media (max-width: 768px) {
  .bento-grid { grid-template-columns: 1fr; }
  .bento-card.wide { grid-column: span 1; }
  .dashboard-layout { grid-template-columns: 1fr; }
  .sidebar { display: none; }
  .app-container { padding: var(--space-5); border-radius: var(--radius-lg); }
}
```
