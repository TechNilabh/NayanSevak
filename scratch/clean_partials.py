import glob
import re
import os

for filepath in glob.glob('frontend/templates/hud/screens/*.html'):
    if 'screen_00_welcome' in filepath:
        continue
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Remove ml-[100px] or fixed margin classes
    content = content.replace('ml-[100px]', 'w-full h-full p-6')
    content = content.replace('mt-12', '')
    content = re.sub(r'h-\[calc\(100vh-[^\)]+\)\]', 'h-full', content)
    
    # Remove fixed bottom status strip duplicates
    content = re.sub(r'<div class="fixed bottom-0 left-0 right-0 h-\[30px\].*?</div>', '', content, flags=re.DOTALL)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Partials sanitized successfully!")
