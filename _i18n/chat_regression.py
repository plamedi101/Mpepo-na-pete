import sys, json
from playwright.sync_api import sync_playwright
BASE = sys.argv[1]
import os
ORIG = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flyfast-chat.fr.js'), encoding='utf-8').read()
ok = True
with sync_playwright() as p:
    b = p.chromium.launch()
    for path in ('index.html', 'flyfast-blog/index.html', 'conditions-de-vente.html'):
        outs = []
        for use_orig in (False, True):
            ctx = b.new_context(viewport={'width': 1280, 'height': 900})
            ctx.route('https://**/*', lambda r: r.abort())
            if use_orig:
                ctx.route('**/flyfast-chat.js*', lambda r: r.fulfill(status=200, content_type='application/javascript', body=ORIG))
            page = ctx.new_page()
            page.goto(BASE + path, wait_until='load')
            page.wait_for_timeout(200)
            html = page.evaluate("document.getElementById('ffc-root').outerHTML")
            style = page.evaluate("[...document.querySelectorAll('style')].map(s => s.textContent).filter(t => t.includes('.ffc'))[0] || ''")
            outs.append((html, style))
            ctx.close()
        same = outs[0] == outs[1]
        ok &= same
        print(('IDENTIQUE ' if same else 'DIFFÉRENT  ') + path, len(outs[0][0]), len(outs[1][0]))
    b.close()
sys.exit(0 if ok else 1)
