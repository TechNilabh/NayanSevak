import os
import re

files = [
    ('screen_01_cockpit.html', 'temp_screens/screen_01_cockpit.html'),
    ('screen_02_takeover.html', 'temp_screens/screen_02_takeover.html'),
    ('screen_03_sensor_primary.html', 'temp_screens/screen_03_sensor_primary.html'),
    ('screen_04_analytics.html', 'temp_screens/screen_04_analytics.html'),
    ('screen_05_calibration.html', 'temp_screens/screen_05_calibration.html'),
    ('screen_06_ar_dashcam.html', 'temp_screens/screen_06_ar_dashcam.html'),
    ('screen_07_boot.html', 'temp_screens/screen_07_boot.html'),
    ('screen_08_logs.html', 'temp_screens/screen_08_logs.html'),
    ('screen_09_voice.html', 'temp_screens/screen_09_voice.html'),
    ('screen_10_sensor_error.html', 'temp_screens/screen_10_sensor_error.html'),
    ('screen_11_summary.html', 'temp_screens/screen_11_summary.html'),
]

overlay_screens = {'screen_02_takeover.html', 'screen_07_boot.html', 'screen_09_voice.html', 'screen_10_sensor_error.html'}

def process_stitch_html(raw_html, filename):
    # Extract inner body content
    match = re.search(r'<body[^>]*>(.*?)</body>', raw_html, re.DOTALL | re.IGNORECASE)
    if match:
        body_content = match.group(1)
    else:
        body_content = raw_html

    # Strip duplicate top <header>, left <nav>, and bottom <footer> tags
    body_content = re.sub(r'<header.*?</header>', '', body_content, flags=re.DOTALL | re.IGNORECASE)
    body_content = re.sub(r'<nav.*?</nav>', '', body_content, flags=re.DOTALL | re.IGNORECASE)
    body_content = re.sub(r'<footer.*?</footer>', '', body_content, flags=re.DOTALL | re.IGNORECASE)
    body_content = re.sub(r'<div class="fixed bottom-0 left-0 right-0 h-\[30px\].*?</div>', '', body_content, flags=re.DOTALL | re.IGNORECASE)

    # Strip fixed margins that collide with global chrome (e.g. ml-[100px], mt-12)
    body_content = body_content.replace('ml-[100px]', '')
    body_content = body_content.replace('mt-12', '')
    body_content = body_content.replace('h-[calc(100vh-48px-80px)]', 'h-full')
    body_content = body_content.replace('h-[calc(100vh-48px)]', 'h-full')

    body_content = body_content.strip()

    if filename in overlay_screens:
        # Wrap overlay screens in .hud-overlay
        return f'<div class="hud-overlay w-full h-full flex flex-col items-center justify-center p-6">{body_content}</div>'
    else:
        return f'<div class="w-full h-full flex flex-col">{body_content}</div>'

os.makedirs('frontend/templates/hud/screens', exist_ok=True)

for target_file, src_file in files:
    if os.path.exists(src_file):
        with open(src_file, 'r', encoding='utf-8', errors='ignore') as f:
            raw = f.read()
        processed = process_stitch_html(raw, target_file)
        out_path = os.path.join('frontend/templates/hud/screens', target_file)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(processed)
        print(f'Restored exact Stitch screen: {target_file}')
