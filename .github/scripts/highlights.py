"""Build assets/highlights.svg from highlights.json."""
import html, json, os, sys

SANS = "'Segoe UI',Helvetica,Arial,sans-serif"
TXT, MUT = '#e6edf3', '#8b98a9'
COLORS = {'red': '#ff4d5a', 'ice': '#9ad7ff', 'amber': '#ffb454'}

def build(cfg):
    tiles = cfg['tiles'][:3]
    n, tw, gap = len(tiles), 270, 15
    x0 = (900 - (n * tw + (n - 1) * gap)) / 2
    s = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 140" width="900" height="140" role="img" aria-label="Highlights">'
         '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b0f17"/><stop offset="1" stop-color="#151d2b"/></linearGradient>'
         '<linearGradient id="sh" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".10"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
         '<clipPath id="tiles">')
    for i in range(n):
        s += f'<rect x="{x0 + i*(tw+gap):.0f}" y="10" width="{tw}" height="120" rx="14"/>'
    s += '</clipPath></defs>'
    for i, t in enumerate(tiles):
        x = x0 + i * (tw + gap)
        col = COLORS.get(t.get('color', 'red'), t.get('color', '#ff4d5a'))
        col = html.escape(col)
        big = html.escape(str(t['big']))
        size = 44 if len(big) <= 3 else 34
        lines = [html.escape(str(l)) for l in t.get('lines', [])][:2]
        s += (f'<rect x="{x:.0f}" y="10" width="{tw}" height="120" rx="14" fill="url(#bg)"/>'
              f'<rect x="{x+.5:.1f}" y="10.5" width="{tw-1}" height="119" rx="14" fill="none" stroke="#fff" stroke-opacity=".12"/>'
              f'<rect x="{x+22:.0f}" y="104" width="46" height="3" rx="1.5" fill="{col}"/>'
              f'<text x="{x+22:.0f}" y="86" font-family="{SANS}" font-size="{size}" font-weight="800" fill="{col}">{big}</text>'
              f'<text x="{x+112:.0f}" y="52" font-family="{SANS}" font-size="14" font-weight="700" fill="{TXT}">{html.escape(str(t["title"]))}</text>')
        for k, line in enumerate(lines):
            s += f'<text x="{x+112:.0f}" y="{74 + k*18}" font-family="{SANS}" font-size="12" fill="{MUT}">{line}</text>'
    s += ('<g clip-path="url(#tiles)"><rect x="-200" y="0" width="200" height="140" fill="url(#sh)">'
          '<animateTransform attributeName="transform" type="translate" from="0 0" to="1150 0" dur="5s" repeatCount="indefinite"/></rect></g></svg>')
    return s

if __name__ == '__main__':
    root = os.getcwd()
    cfg = json.load(open(os.path.join(root, 'highlights.json'), encoding='utf-8'))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'assets', 'highlights.svg')
    open(out, 'w', encoding='utf-8').write(build(cfg))
    print('ok', len(cfg['tiles']), 'tiles')
