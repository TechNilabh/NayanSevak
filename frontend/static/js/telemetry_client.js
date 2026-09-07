/**
 * Telemetry Client - Live Perception & Sensor Polling Service
 * Periodically polls /api/telemetry/latest and updates DOM tabular-numeric
 * elements, SVG gauge arcs, and warning status badges.
 *
 * CRITICAL auto-navigation:
 *   When tier === "CRITICAL" the client auto-navigates to screen_02_takeover,
 *   injecting hazard context (distance, type) via HUDRouter.navigateTo(id, payload).
 *   The screen is NOT auto-dismissed when tier drops — leave that to the user.
 */

const TelemetryClient = (function () {
    let pollingInterval = null;
    const POLL_RATE_MS = 250; // 4Hz real-time update loop

    // Real-time telemetry state (seeded with safe defaults)
    const state = {
        yoloConfidence: 0,
        sensorWeight: 25,     // whole-number %
        cameraWeight: 75,     // whole-number %
        fusionScore: 0,
        tier: 'NOMINAL',
        alert: false,
        mpuVibration: 0.0,    // g-force (peak window value)
        ultrasonicDistance: 200,
        rearDistance: 60,
        visibilityScore: 1.0,
        weather: 'sunny',
        aiFps: 0,
        batteryPct: 84,
        speedKmh: 68,
        tirePressurePsi: 38,
        timestamp: Date.now() / 1000,
    };

    function startPolling() {
        console.log('[TelemetryClient] Starting live telemetry polling stream (4Hz)...');
        stopPolling();
        pollingInterval = setInterval(fetchLatestTelemetry, POLL_RATE_MS);
        updateClockLoop();
    }

    function stopPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
    }

    async function fetchLatestTelemetry() {
        try {
            const res = await fetch('/api/telemetry/latest');
            if (res.ok) {
                const data = await res.json();
                Object.assign(state, data);
            } else {
                simulateLiveTelemetry();
            }
        } catch (err) {
            // Graceful fallback to realistic live physics simulation
            simulateLiveTelemetry();
        }

        updateUI();
        checkCriticalTier();
    }

    function simulateLiveTelemetry() {
        // Subtle realistic jitter simulation (fallback only, no real data)
        state.yoloConfidence = Math.min(99, Math.max(0, state.yoloConfidence + (Math.random() * 4 - 2)));
        state.mpuVibration   = Math.min(2.5, Math.max(0.05, state.mpuVibration + (Math.random() * 0.1 - 0.05)));
        state.ultrasonicDistance = Math.min(300, Math.max(25, state.ultrasonicDistance + (Math.random() * 6 - 3)));
        state.rearDistance   = Math.min(150, Math.max(15, state.rearDistance + (Math.random() * 4 - 2)));
        state.aiFps          = Math.floor(Math.min(36, Math.max(28, state.aiFps + (Math.random() * 2 - 1))));
        state.fusionScore    = Math.round(state.yoloConfidence * 0.88 + (100 - state.mpuVibration * 10) * 0.12);
    }

    // ------------------------------------------------------------------
    // CRITICAL tier → auto-navigate to hazard takeover screen
    // ------------------------------------------------------------------

    function checkCriticalTier() {
        if (
            state.tier === 'CRITICAL' &&
            typeof HUDRouter !== 'undefined' &&
            HUDRouter.getActiveScreen() !== 'screen_02_takeover'
        ) {
            // Determine hazard type from last known state:
            //   simple heuristic mirroring the backend (vibration vs ultrasonic)
            //   cameraWeight/sensorWeight are percentages here; we use ultrasonicDistance
            //   as the distance to show. The "type" field may arrive in future payload.
            const hazardType = state.mpuVibration >= (1 - state.ultrasonicDistance / 400)
                ? 'pothole'
                : 'obstacle';

            HUDRouter.navigateTo('screen_02_takeover', {
                distance: Math.round(state.ultrasonicDistance),
                type: hazardType,
            });
        }
    }

    // ------------------------------------------------------------------
    // DOM updates
    // ------------------------------------------------------------------

    function updateUI() {
        updateElementText('[data-telemetry="yolo-conf"]',    `${Math.round(state.yoloConfidence)}%`);
        updateElementText('[data-telemetry="fusion-score"]', `${Math.round(state.fusionScore)}`);
        updateElementText('[data-telemetry="mpu-vib"]',      `${state.mpuVibration.toFixed(2)} g`);
        updateElementText('[data-telemetry="sonar-dist"]',   `${Math.round(state.ultrasonicDistance)} cm`);
        updateElementText('[data-telemetry="fps"]',          `${state.aiFps}`);
        updateElementText('[data-telemetry="speed"]',        `${Math.round(state.speedKmh)}`);
        updateElementText('[data-telemetry="weather"]',      state.weather);
        updateElementText('[data-telemetry="visibility"]',   `${Math.round(state.visibilityScore * 100)}%`);

        // Header Top Bar Battery
        const topBatt = document.getElementById('top-battery');
        if (topBatt) topBatt.textContent = `${state.batteryPct}%`;

        // Ticker Bar — includes weather and tier
        const ticker = document.getElementById('ticker-telemetry');
        if (ticker) {
            const tierLabel = state.tier !== 'NOMINAL' ? ` | TIER: ${state.tier}` : '';
            ticker.textContent =
                `SYS: YOLOv8n @ ${state.aiFps > 0 ? Math.round(1000 / state.aiFps) : '--'}ms` +
                ` | SONAR: ${Math.round(state.ultrasonicDistance)}cm` +
                ` | VIB: ${state.mpuVibration.toFixed(2)}g` +
                ` | FUSION: ${Math.round(state.fusionScore)}%` +
                ` | WX: ${state.weather}` +
                tierLabel;
        }

        // SVG Gauge Arc (YOLO confidence)
        const cyanArc = document.querySelector('.gauge-arc.stroke-secondary-fixed');
        if (cyanArc) {
            const pct = state.yoloConfidence / 100;
            cyanArc.setAttribute('stroke-dasharray', `${Math.round(283 * pct)} 283`);
        }
    }

    function updateElementText(selector, text) {
        document.querySelectorAll(selector).forEach(el => {
            el.textContent = text;
            el.style.fontVariantNumeric = 'tabular-nums';
        });
    }

    function updateClockLoop() {
        setInterval(() => {
            const clockEl = document.getElementById('top-clock');
            if (clockEl) {
                const now = new Date();
                clockEl.textContent = now.toTimeString().split(' ')[0];
            }
        }, 1000);
    }

    return {
        startPolling,
        stopPolling,
        getState: () => ({ ...state }),
    };
})();

document.addEventListener('DOMContentLoaded', () => {
    TelemetryClient.startPolling();
});
