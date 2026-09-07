/**
 * HUD Router - Layout-Only Protocol Navigation
 * Handles clean separation of standard grid screens (in #hud-content) vs full-bleed modal overlays (in #hud-overlay).
 */

const HUDRouter = (function () {
    let activeScreen = 'screen_00_welcome';

    const overlayScreens = new Set([
        'screen_00_welcome',
        'screen_02_takeover',
        'screen_07_boot',
        'screen_09_voice',
        'screen_10_sensor_error'
    ]);

    const screenMap = {
        'screen_00_welcome': '/templates/hud/screens/screen_00_welcome.html',
        'screen_01_cockpit': '/templates/hud/screens/screen_01_cockpit.html',
        'screen_02_takeover': '/templates/hud/screens/screen_02_takeover.html',
        'screen_03_sensor_primary': '/templates/hud/screens/screen_03_sensor_primary.html',
        'screen_04_analytics': '/templates/hud/screens/screen_04_analytics.html',
        'screen_05_calibration': '/templates/hud/screens/screen_05_calibration.html',
        'screen_06_ar_dashcam': '/templates/hud/screens/screen_06_ar_dashcam.html',
        'screen_07_boot': '/templates/hud/screens/screen_07_boot.html',
        'screen_08_logs': '/templates/hud/screens/screen_08_logs.html',
        'screen_09_voice': '/templates/hud/screens/screen_09_voice.html',
        'screen_10_sensor_error': '/templates/hud/screens/screen_10_sensor_error.html',
        'screen_11_summary': '/templates/hud/screens/screen_11_summary.html'
    };

    const screenCache = {};

    async function init() {
        console.log('[HUDRouter] Initializing Layout-Only Navigation Router...');
        await preloadScreens();
        setupDockListeners();
        setupKeyboardHotkeys();

        // Default screen: Screen 00 Welcome
        navigateTo('screen_00_welcome');
    }

    async function preloadScreens() {
        for (const [key, path] of Object.entries(screenMap)) {
            try {
                const res = await fetch(path);
                if (res.ok) {
                    screenCache[key] = await res.text();
                }
            } catch (err) {
                console.warn(`[HUDRouter] Preload warning for ${key}:`, err);
            }
        }
    }

    // ------------------------------------------------------------------
    // Hazard context injection
    // ------------------------------------------------------------------

    /**
     * Inject hazard payload values into [data-telemetry="hazard-*"] elements.
     * Called after screen HTML has been inserted so the elements exist in DOM.
     * @param {Object} payload  — { distance?: number|string, type?: string }
     * @param {Element} root    — container element to search within
     */
    function injectHazardPayload(payload, root) {
        if (!payload || Object.keys(payload).length === 0) return;
        const container = root || document;

        if (payload.distance !== undefined) {
            container.querySelectorAll('[data-telemetry="hazard-distance"]').forEach(el => {
                el.textContent = Math.round(payload.distance);
            });
        }
        if (payload.type !== undefined) {
            container.querySelectorAll('[data-telemetry="hazard-type"]').forEach(el => {
                // Convert "pothole" → "POTHOLE DETECTED", "obstacle" → "OBSTACLE AHEAD" etc.
                const label = payload.type === 'pothole'
                    ? 'POTHOLE DETECTED'
                    : payload.type === 'obstacle'
                        ? 'OBSTACLE AHEAD'
                        : payload.type.toUpperCase();
                el.textContent = label;
            });
        }
    }

    // ------------------------------------------------------------------
    // Navigation
    // ------------------------------------------------------------------

    function navigateTo(screenId, payload) {
        console.log(`[HUDRouter] Navigating to screen: ${screenId}`, payload || '');
        activeScreen = screenId;

        const mainContainer = document.getElementById('hud-content');
        const overlayContainer = document.getElementById('hud-overlay');
        if (!mainContainer || !overlayContainer) return;

        if (overlayScreens.has(screenId)) {
            // Render inside full-bleed #hud-overlay
            if (screenCache[screenId]) {
                overlayContainer.innerHTML = screenCache[screenId];
                injectHazardPayload(payload, overlayContainer);
            } else {
                fetch(`/templates/hud/screens/${screenId}.html`)
                    .then(r => r.text())
                    .then(html => {
                        screenCache[screenId] = html;
                        overlayContainer.innerHTML = html;
                        injectHazardPayload(payload, overlayContainer);
                    });
            }
            overlayContainer.classList.remove('hidden');
        } else {
            // Render inside #hud-content under canonical shell
            overlayContainer.classList.add('hidden');
            overlayContainer.innerHTML = ''; // clear overlay content

            if (screenCache[screenId]) {
                mainContainer.innerHTML = screenCache[screenId];
                injectHazardPayload(payload, mainContainer);
            } else {
                fetch(`/templates/hud/screens/${screenId}.html`)
                    .then(r => r.text())
                    .then(html => {
                        screenCache[screenId] = html;
                        mainContainer.innerHTML = html;
                        injectHazardPayload(payload, mainContainer);
                    });
            }
        }

        updateDockState(screenId);

        // Special auto-advance for Screen 07 System Boot
        if (screenId === 'screen_07_boot') {
            setTimeout(() => {
                navigateTo('screen_01_cockpit');
            }, 2500);
        }
    }

    function closeOverlay() {
        const overlayContainer = document.getElementById('hud-overlay');
        if (overlayContainer) {
            overlayContainer.classList.add('hidden');
            overlayContainer.innerHTML = '';
        }
        if (overlayScreens.has(activeScreen)) {
            navigateTo('screen_01_cockpit');
        }
    }

    function updateDockState(screenId) {
        document.querySelectorAll('#dock-nav .dock-item').forEach(item => {
            const targetScreen = item.getAttribute('data-screen');
            if (targetScreen === screenId) {
                item.classList.add('active-dock', 'bg-[#00e3fd]/20', 'text-[#00E5FF]');
            } else {
                item.classList.remove('active-dock', 'bg-[#00e3fd]/20', 'text-[#00E5FF]');
            }
        });
    }

    function setupDockListeners() {
        document.querySelectorAll('#dock-nav [data-screen]').forEach(item => {
            item.onclick = (e) => {
                e.preventDefault();
                const target = item.getAttribute('data-screen');
                navigateTo(target);
            };
        });
    }

    function setupKeyboardHotkeys() {
        document.addEventListener('keydown', (e) => {
            if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

            switch (e.code) {
                case 'Space':
                    e.preventDefault();
                    navigateTo('screen_02_takeover');
                    break;
                case 'KeyF':
                    e.preventDefault();
                    navigateTo(activeScreen === 'screen_03_sensor_primary' ? 'screen_01_cockpit' : 'screen_03_sensor_primary');
                    break;
                case 'KeyV':
                    e.preventDefault();
                    navigateTo('screen_09_voice');
                    break;
                case 'Escape':
                    e.preventDefault();
                    if (overlayScreens.has(activeScreen)) {
                        closeOverlay();
                    } else {
                        navigateTo('screen_01_cockpit');
                    }
                    break;
            }
        });
    }

    return {
        init,
        navigateTo,
        closeOverlay,
        getActiveScreen: () => activeScreen
    };
})();

document.addEventListener('DOMContentLoaded', () => {
    HUDRouter.init();
});
