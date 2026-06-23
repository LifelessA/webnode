# ANIMATIONS SKILL

## Required @keyframes (include ALL in every CSS file)
```css
@keyframes fadeUp   { from { opacity:0; transform:translateY(20px) } to { opacity:1; transform:translateY(0) } }
@keyframes fadeIn   { from { opacity:0 } to { opacity:1 } }
@keyframes slideIn  { from { opacity:0; transform:translateX(-12px) } to { opacity:1; transform:translateX(0) } }
@keyframes slideUp  { from { opacity:0; transform:translateY(12px) } to { opacity:1; transform:translateY(0) } }
@keyframes scaleIn  { from { opacity:0; transform:scale(0.92) } to { opacity:1; transform:scale(1) } }
@keyframes spin     { to { transform:rotate(360deg) } }
@keyframes pulse-glow {
  0%,100% { box-shadow: 0 0 10px var(--accent-glow); }
  50%      { box-shadow: 0 0 25px var(--accent-glow), 0 0 50px rgba(99,102,241,0.2); }
}
@keyframes shimmer {
  0%   { background-position: -200% center; }
  100% { background-position:  200% center; }
}
```

## How to apply animations
- Page container on load: `animation: fadeUp 0.5s ease both`
- List items added by JS: `animation: slideIn 0.2s ease both`
- Modal/overlay appearing: `animation: scaleIn 0.25s cubic-bezier(0.34,1.56,0.64,1) both`
- Active/pulsing element: `animation: pulse-glow 2s ease-in-out infinite`
- Loading skeleton: `background: linear-gradient(90deg, var(--surface) 25%, var(--surface-2) 50%, var(--surface) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite`

## JS: stagger animation for dynamically added items
```javascript
// When adding multiple items to a list, stagger their animation
items.forEach((item, index) => {
  item.style.animationDelay = `${index * 60}ms`;
  item.classList.add('animate-slide-in');
});
```
