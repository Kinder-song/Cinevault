# CineVault Light Theme Design Spec

## Overview
Add a light theme ("Glass Light Macaron") to CineVault while preserving the dark theme. Theme toggle button placed next to username.

---

## Color Palette: Glass Light Macaron

| Role | Color | Description |
|------|-------|-------------|
| Background | `#F5F7FA` | Light gray-white |
| Surface | `rgba(255, 255, 255, 0.7)` | Semi-transparent white glass |
| Glass Border | `rgba(255, 255, 255, 0.2)` | Glass border |
| Accent Frost Blue | `#89B4E8` | Macaron blue accent |
| Accent Macaron Pink | `#F0B5D4` | Macaron pink accent |
| Text Primary | `rgba(30, 40, 60, 0.9)` | Deep blue-gray text |
| Text Secondary | `rgba(30, 40, 60, 0.6)` | Secondary text |

---

## Design Details

### Navigation Bar (Light)
- Background: `rgba(255, 255, 255, 0.8)` + `backdrop-filter: blur(20px)`
- Brand logo: Same style, dark text

### Video Cards (Light)
- Card background: `rgba(255, 255, 255, 0.6)` + `backdrop-filter: blur(16px)`
- Glass border: `rgba(255, 255, 255, 0.2)`
- Hover: subtle lift + enhanced shadow

### Theme Toggle Button
- Position: Next to username in nav bar
- Icon: Sun (light mode) / Moon (dark mode)
- Color: Macaron blue `#89B4E8`
- Hover: Pink glow effect `rgba(240, 181, 212, 0.5)`

### Placeholder Gradient (Light)
- Change from blue-gray to light blue-pink gradient

---

## Theme Toggle Implementation

### CSS Strategy
- Use CSS custom properties (variables) for all colors
- `[data-theme="light"]` and `[data-theme="dark"]` selectors
- Default: dark theme
- Toggle adds/removes `[data-theme="light"]` on `<html>`

### JavaScript
- Save preference to `localStorage`
- On load, check localStorage for preference
- Smooth transition on toggle (0.3s)

### Button Design
- Sun icon: when in dark mode (click to switch to light)
- Moon icon: when in light mode (click to switch to dark)
- Hover: scale(1.1) + glow effect

---

## Implementation Files

1. `static/css/style.css` - Add light theme variables and styles
2. `static/js/main.js` - Add theme toggle logic
3. `templates/base.html` - Add theme toggle button to nav