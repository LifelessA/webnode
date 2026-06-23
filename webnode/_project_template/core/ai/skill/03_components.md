# COMPONENT PATTERNS SKILL

Copy these CSS patterns exactly for common UI components.

## Glassmorphism Card
```css
.glass-card {
  background: rgba(255,255,255,0.04);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  position: relative;
  overflow: hidden;
  transition: border-color 0.25s, transform 0.25s;
}
.glass-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
}
.glass-card:hover { border-color: rgba(255,255,255,0.2); transform: translateY(-3px); }
```

## Primary Button
```css
.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: 12px 24px;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  color: #fff;
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 600;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: 0 4px 15px rgba(99,102,241,0.3);
}
.btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(99,102,241,0.5); }
.btn-primary:active { transform: translateY(0); }
```

## Ghost Button
```css
.btn-ghost {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: 10px 20px;
  background: transparent;
  color: var(--text);
  font-size: 14px;
  font-weight: 500;
  border: 1px solid var(--border-2);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s, transform 0.2s;
}
.btn-ghost:hover { background: var(--surface-2); border-color: rgba(255,255,255,0.25); transform: translateY(-1px); }
```

## Input Field
```css
.input-field {
  width: 100%;
  padding: 12px 16px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border-2);
  border-radius: var(--radius-md);
  color: var(--text);
  font-family: var(--font-body);
  font-size: 15px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.input-field::placeholder { color: var(--text-muted); }
.input-field:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(99,102,241,0.15); }
```

## Badge / Tag
```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  background: rgba(99,102,241,0.15);
  border: 1px solid rgba(99,102,241,0.3);
  border-radius: 999px;
  color: var(--accent);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.badge.success { background: rgba(16,185,129,0.15); border-color: rgba(16,185,129,0.3); color: var(--success); }
.badge.danger  { background: rgba(239,68,68,0.15);  border-color: rgba(239,68,68,0.3);  color: var(--danger);  }
.badge.warning { background: rgba(245,158,11,0.15); border-color: rgba(245,158,11,0.3); color: var(--warning); }
```

## List Item
```css
.list-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  transition: background 0.15s, border-color 0.15s;
  margin-bottom: var(--space-2);
}
.list-item:hover { background: var(--surface-2); border-color: var(--border-2); }
.list-item.completed .item-text { text-decoration: line-through; color: var(--text-muted); opacity: 0.6; }
```

## Heading Styles
```css
.heading-xl {
  font-family: var(--font-heading);
  font-size: clamp(2rem, 5vw, 4rem);
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #fff 30%, rgba(255,255,255,0.5));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.heading-gradient {
  font-family: var(--font-heading);
  font-size: clamp(1.5rem, 3vw, 2.5rem);
  font-weight: 700;
  background: linear-gradient(135deg, var(--accent), var(--accent-2), #ec4899);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
```

## Divider
```css
.divider { height: 1px; background: linear-gradient(90deg, transparent, var(--border-2), transparent); margin: var(--space-6) 0; }
```

## Scrollbar
```css
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-2); border-radius: 999px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.25); }
```
