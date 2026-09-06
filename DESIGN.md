# DESIGN.md - Nayan Sevak AI Dashboard Design System Tokens

## Color Palette

| Token | Hex Value | Application |
|---|---|---|
| `--color-bg-base` | `#0A0C10` | Base cockpit dark stage & background |
| `--color-bg-card` | `#12161F` | Glassmorphic card surface |
| `--color-bg-card-hover` | `#1A202C` | Interactive hover state |
| `--color-border-glass` | `rgba(255, 255, 255, 0.08)` | Subtle translucent glass borders |
| `--color-accent-cyan` | `#00E5FF` | Primary HUD active highlights, telemetry status, key indicators |
| `--color-accent-cyan-glow` | `rgba(0, 229, 255, 0.3)` | Neon glow box-shadow & drop-shadow |
| `--color-accent-amber` | `#FFB300` | Warnings, caution alerts, tire pressure, MPU6050 spikes |
| `--color-accent-red` | `#FF1744` | Hazard takeovers, emergency brake alerts, sensor disconnects |
| `--color-text-primary` | `#F0F4F8` | High-contrast body text & main values |
| `--color-text-secondary` | `#8A99AD` | Muted labels, secondary telemetry, captions |
| `--color-text-disabled` | `#4A5568` | Inactive status text & offline indicators |

## Typography

- **Headers & Display Titles**: `Titillium Web`, sans-serif (Font Weight: 600 / 700)
- **Body & Controls**: `Inter`, system-ui, sans-serif (Font Weight: 400 / 500)
- **Gauges & Telemetry Numbers**: `IBM Plex Mono`, monospace
  - MUST enforce: `font-variant-numeric: tabular-nums` to prevent dynamic layout shifts during live data updates.

## Component Specifications

### 1. Left Dock Navigation (`#dock-nav`)
- **Dimensions**: Fixed 64px width floating pill, 32px border-radius.
- **Background**: Glassmorphic dark backdrop (`rgba(18, 22, 31, 0.75)` with `backdrop-filter: blur(16px)`).
- **Icons**: Shield Emblem (Logo), Cockpit (Flight Deck), Live AR, Hazard Logs, Analytics, Calibration, Warning Triangle.

### 2. Top Status Bar (`#top-hud-bar`)
- **Height**: 48px floating glass bar.
- **Sections**:
  - Left: Real-time clock & weather widget pill.
  - Center: Transmission selector (`P R N D` with illuminated cyan `D`).
  - Right: Synced 5G signal status, AI readiness badge, and battery percentage indicator.

### 3. Glassmorphic Cards & Gauges
- **Border**: 1px solid `rgba(255, 255, 255, 0.08)`.
- **Glow**: Dynamic cyan drop-shadow on focus/active states.
- **SVG / Canvas Gauges**: Radial speedometers, ultrasonic proximity arcs, and vibration spectrum graphs.
