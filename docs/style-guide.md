# Design System — Babloo (Federal Ka Manjan)

**Overall aesthetic:** Dark, space-themed UI with a starfield background. Minimalist and modern, inspired by SaaS landing pages. Font is **Inter** throughout.

## Color Palette

| Role | Value |
|---|---|
| Background (landing) | `#05050f` |
| Background (app) | `#0a0a0f` |
| Surface layer 1 | `#111118` |
| Surface layer 2 | `#1a1a24` |
| Primary text | `#f0f0f3` |
| Muted/secondary text | `#8b8b9e` |
| Borders | `rgba(255,255,255,0.08)` |
| Accent / interactive | `#3b82f6` |
| Accent hover | `#2563eb` |
| Glass surfaces | `rgba(255,255,255,0.03–0.06)` + `backdrop-filter: blur` |

## Glow / Lighting Effects

- **Central hero glow:** Large purple radial gradient (`rgba(109,40,217,0.22)`) bleeding into soft blue (`rgba(59,130,246,0.12)`) — sits behind everything
- **Logo glow:** Animated pulsing gold/amber radial gradient (`rgba(255,200,50,0.55)` → `rgba(212,170,0,0.25)`), scales gently on a 3s loop
- **Logo drop-shadow:** Gold `rgba(255,200,50,0.6)`
- **CTA button glow:** Purple `rgba(124,58,237,0.45)`, intensifies on hover

## Typography

- **Hero title:** 900 weight, fluid size (`clamp(3.2rem, 10vw, 6rem)`), white-to-lavender gradient (`#ffffff` → `#c4b5fd`), tight letter-spacing `-0.04em`
- **Tagline:** Uppercase, wide letter-spacing, violet `#a78bfa`
- **Body/sub:** Muted gray, `line-height: 1.6`

## UI Components

- **CTA button:** Pill-shaped (`border-radius: 999px`), purple-to-indigo gradient (`#7c3aed` → `#4f46e5`), lifts on hover
- **Announcement pill:** Subtle glass border, dark fill, indigo badge
- **Chat bubbles:** User = blue gradient; Assistant = near-transparent glass
- **Header:** Frosted glass (`blur(20px)`) with border-bottom

## Motion

Minimal — only the logo pulse animation (`3s ease-in-out infinite`) and button hover lift (`translateY(-2px) scale(1.03)`).
