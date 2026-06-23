# DESIGN SYSTEM SKILL

## Mandatory Font Import (in every HTML <head>)
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;700;800;900&display=swap" rel="stylesheet">
```

## Mandatory CSS Root Variables (start every CSS file with this)
```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:           #080b14;
  --bg-2:         #0d1117;
  --surface:      rgba(255, 255, 255, 0.04);
  --surface-2:    rgba(255, 255, 255, 0.08);
  --border:       rgba(255, 255, 255, 0.08);
  --border-2:     rgba(255, 255, 255, 0.16);
  --text:         #e2e8f0;
  --text-muted:   #64748b;
  --accent:       #6366f1;
  --accent-2:     #8b5cf6;
  --accent-glow:  rgba(99, 102, 241, 0.35);
  --success:      #10b981;
  --danger:       #ef4444;
  --warning:      #f59e0b;

  --space-1: 4px;   --space-2: 8px;   --space-3: 12px;
  --space-4: 16px;  --space-5: 20px;  --space-6: 24px;
  --space-8: 32px;  --space-10: 40px; --space-12: 48px;

  --radius-sm: 6px;  --radius-md: 10px;
  --radius-lg: 16px; --radius-xl: 24px;

  --font-body:    'Inter', system-ui, sans-serif;
  --font-heading: 'Outfit', system-ui, sans-serif;

  --shadow-sm: 0 1px 3px rgba(0,0,0,0.4);
  --shadow-md: 0 4px 16px rgba(0,0,0,0.5);
  --shadow-lg: 0 8px 32px rgba(0,0,0,0.6);
  --glow-accent: 0 0 20px var(--accent-glow), 0 0 40px rgba(99,102,241,0.15);
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  font-size: 16px;
  line-height: 1.6;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}
```

## NEVER DO
- ❌ White background on body
- ❌ Default browser button/input styles
- ❌ Plain black text on white
- ❌ No padding (elements touching browser edge)
- ❌ Inline CSS for design (use classes)
- ❌ Missing `<link rel="stylesheet">` in HTML head
- ❌ Font-size below 13px for body text
